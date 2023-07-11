import sentry_sdk
import tornado.web

import common.lib.noq_json as json
from api.handlers.utils import get_paginated_typeahead_response
from common import Tenant
from common.aws.iam.policy.utils import (
    get_aws_managed_policy_arns,
    list_customer_managed_policy_definitions,
)
from common.aws.iam.role.models import IAMRole
from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, InvalidRequest
from common.handlers.base import BaseHandler
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.asyncio import aio_wrapper
from common.lib.auth import get_accounts_user_can_view_resources_for
from common.lib.aws.typeahead_cache import get_all_resource_arns
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler, redis_get
from common.models import ArnArray, TypeAheadPaginatedRequestQueryParams, WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


async def handle_aws_resource_type_ahead_request_for_all(
    user: str,
    groups: list[str],
    tenant_name: str,
    resource_arn: str,
    page: int,
    page_size: int,
) -> list[str]:
    resource_arn = resource_arn.lower()
    max_results = page * page_size
    red = await RedisHandler().redis(tenant_name)
    resource_redis_cache_key = config.get_tenant_specific_key(
        "aws_config_cache.redis_key",
        tenant_name,
        f"{tenant_name}_AWSCONFIG_RESOURCE_CACHE",
    )
    all_resource_arns = await aio_wrapper(red.hkeys, resource_redis_cache_key)
    # Fall back to DynamoDB or S3?
    if not all_resource_arns:
        s3_bucket = config.get_tenant_specific_key(
            "aws_config_cache_combined.s3.bucket", tenant_name
        )
        s3_key = config.get_tenant_specific_key(
            "aws_config_cache_combined.s3.file",
            tenant_name,
            "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
        )
        try:
            all_resources = await retrieve_json_data_from_redis_or_s3(
                s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant_name, default={}
            )
            all_resource_arns = all_resources.keys()
            if all_resources:
                await aio_wrapper(red.hmset, resource_redis_cache_key, all_resources)
        except DataNotRetrievable:
            sentry_sdk.capture_exception()
            all_resource_arns = []

    # Fall back to All Resource ARN Cache
    if not all_resource_arns:
        all_resource_arns = await get_all_resource_arns(tenant_name)

    allowed_accounts_for_viewing_resources = (
        await get_accounts_user_can_view_resources_for(user, groups, tenant_name)
    )

    matching = set()
    for arn in all_resource_arns:
        if len(matching) >= max_results:
            break
        if arn.split(":")[4] not in allowed_accounts_for_viewing_resources:
            continue
        if resource_arn in arn.lower():
            matching.add(arn)

    arn_array = ArnArray.parse_obj((list(matching)))
    return [arn for arn in arn_array.__root__][
        (page - 1) * page_size : page * page_size
    ]


async def handle_aws_resource_type_ahead_request(
    user: str,
    groups: list[str],
    tenant: Tenant,
    service: str,
    page: int,
    page_size: int,
    template_id: str = None,
    resource_id: str = None,
    provider_definitions_ids: list[str] = None,
    aws_managed_only: bool = False,
) -> list[str]:
    if service != "managed_policy" and aws_managed_only:
        raise InvalidRequest(
            "The aws_managed_only parameter is only supported for managed_policy"
        )

    if service == "all":
        return await handle_aws_resource_type_ahead_request_for_all(
            user, groups, tenant.name, resource_id, page, page_size
        )

    account_id = None
    topic_is_hash = True
    resource_id = resource_id.lower()
    max_results = page * page_size
    allowed_accounts_for_viewing_resources = (
        await get_accounts_user_can_view_resources_for(user, groups, tenant.name)
    )

    if service == "managed_policy":
        policy_arns = await get_aws_managed_policy_arns()
        if resource_id:
            policy_arns = [arn for arn in policy_arns if resource_id in arn.lower()]

        if not aws_managed_only:
            mp_defs = await list_customer_managed_policy_definitions(
                tenant, resource_id, provider_definitions_ids
            )
            # Prioritize customer managed policies
            policy_arns = [
                mp_def.secondary_resource_id for mp_def in mp_defs
            ] + policy_arns

        return policy_arns[(page - 1) * page_size : page * page_size]

    role_name = bool(service == "iam_role")
    if service in ["iam_arn", "iam_role"]:
        filter_condition = None
        if account_id:
            filter_condition = IAMRole.accountId == account_id
        iam_roles = await IAMRole.query(
            tenant.name,
            filter_condition=filter_condition,
            attributes_to_get=["tenant", "accountId", "name", "arn", "resourceId"],
        )
        data = {iam_role.arn: iam_role.dict() for iam_role in iam_roles}
    else:
        if service == "s3":
            topic = config.get_tenant_specific_key(
                "redis.s3_bucket_key", tenant.name, f"{tenant.name}_S3_BUCKETS"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.bucket", tenant.name
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.file",
                tenant.name,
                "account_resource_cache/cache_s3_combined_v1.json.gz",
            )
        elif service == "sqs":
            topic = config.get_tenant_specific_key(
                "redis.sqs_queues_key", tenant.name, f"{tenant.name}_SQS_QUEUES"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.sqs_combined.bucket", tenant.name
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.sqs_combined.file",
                tenant.name,
                "account_resource_cache/cache_sqs_queues_combined_v1.json.gz",
            )
        elif service == "sns":
            topic = config.get_tenant_specific_key(
                "redis.sns_topics_key", tenant.name, f"{tenant.name}_SNS_TOPICS"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.sns_topics_combined.bucket",
                tenant.name,
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.sns_topics_topics_combined.file",
                tenant.name,
                "account_resource_cache/cache_sns_topics_combined_v1.json.gz",
            )
        elif service == "account":
            topic = None
            s3_bucket = None
            s3_key = None
            topic_is_hash = False
        elif service == "app":
            topic = config.get_tenant_specific_key(
                "celery.apps_to_roles.redis_key",
                tenant.name,
                f"{tenant.name}_APPS_TO_ROLES",
            )
            s3_bucket = None
            s3_key = None
            topic_is_hash = False
        else:
            raise InvalidRequest("Invalid service specified")

        if not topic and service != "account":
            raise InvalidRequest("Invalid service specified")

        if topic and topic_is_hash and s3_key:
            data = await retrieve_json_data_from_redis_or_s3(
                redis_key=topic,
                redis_data_type="hash",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                tenant=tenant.name,
            )
        elif topic:
            data = await redis_get(topic, tenant.name)

    results: list[dict] = []

    unique_roles: list[str] = []

    if service == "account":
        account_ids_to_names = await get_account_id_to_name_mapping(tenant.name)
        for account_id, account_name in account_ids_to_names.items():
            account_str = f"{account_name} ({account_id})"
            if resource_id in account_str.lower():
                results.append(account_str)
    else:
        if not data:
            return []
        for k, v in data.items():
            if account_id and k != account_id:
                continue
            elif k not in allowed_accounts_for_viewing_resources:
                continue

            if role_name:
                try:
                    r = k.split("role/")[1]
                except IndexError:
                    continue
                if resource_id in r.lower():
                    if r not in unique_roles:
                        unique_roles.append(r)
                        results.append(r)
            elif service == "iam_arn":
                if k.startswith("arn:") and resource_id in k.lower():
                    results.append(k)
            else:
                list_of_items = json.loads(v)
                for item in list_of_items:
                    if service == "s3":
                        item = f"arn:aws:s3:::{item}"
                    if resource_id in item.lower():
                        results.append(item)
                    if len(results) > max_results:
                        break
            if len(results) > max_results:
                break

    return results[(page - 1) * page_size : page * page_size]


class AWSResourceQueryParams(TypeAheadPaginatedRequestQueryParams):
    resource_id: str = None
    aws_managed_only: bool = False
    page_size: int = 50


class AWSResourceTypeAheadHandler(BaseHandler):
    async def get(self, service: str = None):
        """
        GET /api/v4/self-service/typeahead/aws/service/${service} - Returns list of matching resource ARNs.
        """
        query_params = AWSResourceQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        try:
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    **get_paginated_typeahead_response(
                        await handle_aws_resource_type_ahead_request(
                            self.user,
                            self.groups,
                            self.ctx.db_tenant,
                            service,
                            **query_params.dict(exclude_none=True),
                        ),
                        query_params,
                    ),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except InvalidRequest as err:
            self.set_status(400)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        except Exception as err:
            self.set_status(500)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            log.error(
                {
                    "message": "Error in AWSResourceTypeAheadHandler",
                    "error": repr(err),
                },
                exc_info=True,
            )
            raise tornado.web.Finish()
