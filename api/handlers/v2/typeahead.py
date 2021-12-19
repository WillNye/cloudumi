from typing import Optional

import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async

from common.config import config
from common.exceptions.exceptions import DataNotRetrievable
from common.handlers.base import BaseAPIV2Handler
from common.lib.aws.typeahead_cache import get_all_resource_arns
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.redis import RedisHandler
from common.models import ArnArray


class ResourceTypeAheadHandlerV2(BaseAPIV2Handler):
    async def get(self):
        host = self.ctx.host
        red = await RedisHandler().redis(host)
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

        resource_redis_cache_key = config.get_host_specific_key(
            "aws_config_cache.redis_key",
            host,
            f"{host}_AWSCONFIG_RESOURCE_CACHE",
        )
        all_resource_arns = await sync_to_async(red.hkeys)(resource_redis_cache_key)
        # Fall back to DynamoDB or S3?
        if not all_resource_arns:
            s3_bucket = config.get_host_specific_key(
                "aws_config_cache_combined.s3.bucket", host
            )
            s3_key = config.get_host_specific_key(
                "aws_config_cache_combined.s3.file",
                host,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            )
            try:
                all_resources = await retrieve_json_data_from_redis_or_s3(
                    s3_bucket=s3_bucket, s3_key=s3_key, host=host, default={}
                )
                all_resource_arns = all_resources.keys()
                if all_resources:
                    await sync_to_async(red.hmset)(
                        resource_redis_cache_key, all_resources
                    )
            except DataNotRetrievable:
                sentry_sdk.capture_exception()
                all_resource_arns = []

        # Fall back to All Resource ARN Cache
        if not all_resource_arns:
            all_resource_arns = await get_all_resource_arns(host)

        matching = set()
        for arn in all_resource_arns:
            if len(matching) >= limit:
                break
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


class SelfServiceStep1ResourceTypeahead(BaseAPIV2Handler):
    async def get(self):
        host = self.ctx.host
        try:
            # Get type ahead request arg
            type_ahead: Optional[str] = (
                self.request.arguments.get("typeahead")[0].decode("utf-8").lower()
            )
        except TypeError:
            type_ahead = None
        if not type_ahead:
            self.write(json.dumps([]))
            return
        max_limit: int = config.get_host_specific_key(
            "self_service_step_1_resource_typeahead.max_limit",
            host,
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

        typehead_data = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get_host_specific_key(
                "cache_self_service_typeahead.redis.key",
                host,
                f"{host}_cache_self_service_typeahead_v1",
            ),
            s3_bucket=config.get_host_specific_key(
                "cache_self_service_typeahead.s3.bucket", host
            ),
            s3_key=config.get_host_specific_key(
                "cache_self_service_typeahead.s3.file",
                host,
                "cache_self_service_typeahead/cache_self_service_typeahead_v1.json.gz",
            ),
            host=host,
            default={},
        )
        matching = []

        for entry in typehead_data.get("typeahead_entries", []):
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
                and type_ahead.lower()
                in entry["principal"]["resource_identifier"].lower()
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
        self.write(json.dumps(matching))
