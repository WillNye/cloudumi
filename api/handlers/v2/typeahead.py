from typing import Optional

import sentry_sdk

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import DataNotRetrievable
from common.handlers.base import BaseAPIV2Handler
from common.lib.asyncio import aio_wrapper
from common.lib.auth import get_accounts_user_can_view_resources_for
from common.lib.aws.typeahead_cache import get_all_resource_arns
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.redis import RedisHandler
from common.models import ArnArray


class ResourceTypeAheadHandlerV2(BaseAPIV2Handler):
    async def get(self):
        tenant = self.ctx.tenant
        red = await RedisHandler().redis(tenant)
        try:
            type_ahead: Optional[str] = (
                self.request.arguments.get("typeahead")[0].decode("utf-8").lower()
            )
        except TypeError:
            type_ahead = None

        try:
            account_id: Optional[str] = self.request.arguments.get("account_id")[
                0
            ].decode("utf-8")
        except TypeError:
            account_id = None

        try:
            resource_type: Optional[str] = self.request.arguments.get("resource_type")[
                0
            ].decode("utf-8")
        except TypeError:
            resource_type = None

        try:
            region: Optional[str] = self.request.arguments.get("region")[0].decode(
                "utf-8"
            )
        except TypeError:
            region = None

        try:
            limit: int = self.request.arguments.get("limit")[0].decode("utf-8")
            if limit:
                limit = int(limit)
        except TypeError:
            limit = 20

        try:
            ui_formatted: Optional[bool] = (
                self.request.arguments.get("ui_formatted")[0].decode("utf-8").lower()
            )
        except TypeError:
            ui_formatted = False

        resource_redis_cache_key = config.get_tenant_specific_key(
            "aws_config_cache.redis_key",
            tenant,
            f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
        )
        all_resource_arns = await aio_wrapper(red.hkeys, resource_redis_cache_key)
        # Fall back to DynamoDB or S3?
        if not all_resource_arns:
            s3_bucket = config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.bucket", tenant
            )
            s3_key = config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.file",
                tenant,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            )
            try:
                all_resources = await retrieve_json_data_from_redis_or_s3(
                    s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant, default={}
                )
                all_resource_arns = all_resources.keys()
                if all_resources:
                    await aio_wrapper(
                        red.hmset, resource_redis_cache_key, all_resources
                    )
            except DataNotRetrievable:
                sentry_sdk.capture_exception()
                all_resource_arns = []

        # Fall back to All Resource ARN Cache
        if not all_resource_arns:
            all_resource_arns = await get_all_resource_arns(tenant)

        allowed_accounts_for_viewing_resources = (
            await get_accounts_user_can_view_resources_for(
                self.user, self.groups, tenant
            )
        )

        matching = set()
        for arn in all_resource_arns:
            if len(matching) >= limit:
                break
            if arn.split(":")[4] not in allowed_accounts_for_viewing_resources:
                continue
            # ARN format: 'arn:aws:sqs:us-east-1:123456789012:resource_name'
            if resource_type and resource_type != arn.split(":")[2]:
                continue
            if region and region != arn.split(":")[3]:
                continue
            if account_id and account_id != arn.split(":")[4]:
                continue
            if type_ahead and type_ahead in arn.lower():
                matching.add(arn)
            elif not type_ahead:
                # Oh, you want all the things do you?
                matching.add(arn)
        arn_array = ArnArray.parse_obj((list(matching)))
        if ui_formatted:
            self.write(json.dumps([{"title": arn} for arn in arn_array.__root__]))
        else:
            self.write(arn_array.json())


async def get_matching_identity_typahead(
    tenant, type_ahead, user, groups, limit=20, max_limit=10000
):
    if not type_ahead:
        return []

    typehead_data = await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get_tenant_specific_key(
            "cache_self_service_typeahead.redis.key",
            tenant,
            f"{tenant}_cache_self_service_typeahead_v1",
        ),
        s3_bucket=config.get_tenant_specific_key(
            "cache_self_service_typeahead.s3.bucket", tenant
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_self_service_typeahead.s3.file",
            tenant,
            "cache_self_service_typeahead/cache_self_service_typeahead_v1.json.gz",
        ),
        tenant=tenant,
        default={},
    )

    allowed_accounts_for_viewing_resources = (
        await get_accounts_user_can_view_resources_for(user, groups, tenant)
    )

    matching = []
    for entry in typehead_data.get("typeahead_entries", []):
        principal_arn = entry.get("principal", {}).get("principal_arn", "")
        if (
            principal_arn
            and principal_arn.split(":")[4]
            not in allowed_accounts_for_viewing_resources
        ):
            continue
        if len(matching) >= limit:
            break
        if (
            entry.get("display_text")
            and type_ahead.lower() in entry["display_text"].lower()
        ):
            matching.append(entry)
            continue
        if (
            entry.get("principal", {}).get("resource_identifier")
            and type_ahead.lower() in entry["principal"]["resource_identifier"].lower()
        ):
            matching.append(entry)
            continue
        if (
            entry.get("principal", {}).get("principal_arn")
            and type_ahead.lower() in entry["principal"]["principal_arn"].lower()
        ):
            matching.append(entry)
            continue
        if (
            entry.get("application_name")
            and type_ahead.lower() in entry["application_name"].lower()
        ):
            matching.append(entry)
            continue
    return matching


class SelfServiceStep1ResourceTypeahead(BaseAPIV2Handler):
    async def get(self):
        tenant = self.ctx.tenant
        try:
            # Get type ahead request arg
            type_ahead: Optional[str] = (
                self.request.arguments.get("typeahead")[0].decode("utf-8").lower()
            )
        except TypeError:
            type_ahead = None
        max_limit: int = config.get_tenant_specific_key(
            "self_service_step_1_resource_typeahead.max_limit",
            tenant,
            10000,
        )
        limit: int = 20
        try:
            # Get limit request arg
            limit_raw: str = self.request.arguments.get("limit")[0].decode("utf-8")
            if limit_raw:
                limit = int(limit_raw)
            if limit > max_limit:
                limit = max_limit
        except TypeError:
            pass
        matching = await get_matching_identity_typahead(
            tenant, type_ahead, self.user, self.groups, limit, max_limit
        )
        self.write(json.dumps(matching))
