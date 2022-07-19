import json
from typing import Dict, Optional

from policy_sentry.util.arns import get_account_from_arn, parse_arn

from common.config import config
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.redis import RedisHandler, redis_hget

log = config.get_logger()


def get_resource_tag(
    resource: Dict,
    key: str,
    is_list: Optional[bool] = False,
    default: Optional[any] = None,
) -> any:
    """
    Retrieves and parses the value of a provided AWS tag.
    :param resource: An AWS resource dictionary
    :param key: key of the tag
    :param is_list: The value for the key is a list type
    :param default: Default value is tag not found
    :return:
    """
    for tag in resource.get("Tags", resource.get("tags", [])):
        if tag.get("Key") == key:
            val = tag.get("Value")
            if is_list:
                return set([] if not val else val.split(":"))
            return val
    return default


async def get_resource_account(arn: str, tenant: str) -> str:
    """Return the AWS account ID that owns a resource.

    In most cases, this will pull the ID directly from the ARN.
    If we are unsuccessful in pulling the account from ARN, we try to grab it from our resources cache
    """
    red = await RedisHandler().redis(tenant)
    resource_account: str = get_account_from_arn(arn)
    if resource_account:
        return resource_account

    resources_from_aws_config_redis_key: str = config.get_tenant_specific_key(
        "aws_config_cache.redis_key",
        tenant,
        f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
    )

    if not red.exists(resources_from_aws_config_redis_key):
        # This will force a refresh of our redis cache if the data exists in S3
        await retrieve_json_data_from_redis_or_s3(
            redis_key=resources_from_aws_config_redis_key,
            s3_bucket=config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.bucket", tenant
            ),
            s3_key=config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.file",
                tenant,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            ),
            redis_data_type="hash",
            tenant=tenant,
            default={},
        )

    resource_info = await redis_hget(resources_from_aws_config_redis_key, arn, tenant)
    if resource_info:
        return json.loads(resource_info).get("accountId", "")
    elif "arn:aws:s3:::" in arn:
        # Try to retrieve S3 bucket information from S3 cache. This is inefficient and we should ideally have
        # retrieved this info from our AWS Config cache, but we've encountered problems with AWS Config historically
        # that have necessitated this code.
        s3_cache = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get_tenant_specific_key(
                "redis.s3_buckets_key", tenant, f"{tenant}_S3_BUCKETS"
            ),
            redis_data_type="hash",
            tenant=tenant,
        )
        search_bucket_name = arn.split(":")[-1]
        for bucket_account_id, buckets in s3_cache.items():
            buckets_j = json.loads(buckets)
            if search_bucket_name in buckets_j:
                return bucket_account_id
    return ""


class ResourceSummary:
    def __init__(
        self,
        tenant: str,
        arn: str,
        account: str,
        partition: str,
        service: str,
        region: str,
        resource_type: str,
        name: str,
        parent_name: str = None,
    ):
        self.tenant = tenant
        self.arn = arn
        self.account = account
        self.partition = partition
        self.service = service
        self.region = region
        self.resource_type = resource_type
        self.name = name
        self.parent_name = parent_name

    @classmethod
    async def set(cls, tenant: str, arn: str) -> "ResourceSummary":
        from common.lib.aws.utils import get_bucket_location_with_fallback

        parsed_arn = parse_arn(arn)
        parsed_arn["arn"] = arn
        account_provided = bool(parsed_arn["account"])

        if not account_provided:
            arn_as_resource = arn
            if parsed_arn["service"] == "s3" and not account_provided:
                arn_as_resource = arn_as_resource.replace(
                    f"/{parsed_arn['resource_path']}", ""
                )

            parsed_arn["account"] = await get_resource_account(arn_as_resource, tenant)
            if not parsed_arn["account"]:
                raise ValueError("Resource account not found")

        if parsed_arn["service"] == "s3":
            parsed_arn["name"] = parsed_arn.pop("resource_path", None)
            if not account_provided:  # Either a bucket or an object
                if parsed_arn["name"]:
                    bucket_name = parsed_arn.pop("resource", "")
                    parsed_arn["resource_type"] = "object"
                    parsed_arn["parent_name"] = bucket_name
                else:
                    bucket_name = parsed_arn.pop("resource", "")
                    parsed_arn["resource_type"] = "bucket"
                    parsed_arn["name"] = bucket_name

                parsed_arn["region"] = await get_bucket_location_with_fallback(
                    bucket_name, parsed_arn["account"], tenant
                )
        else:
            if not parsed_arn["region"]:
                parsed_arn["region"] = config.region

            if resource_path := parsed_arn.pop("resource_path", ""):
                parsed_arn["name"] = resource_path
                parsed_arn["resource_type"] = parsed_arn.pop("resource", "")
            else:
                parsed_arn["name"] = parsed_arn.pop("resource", "")
                parsed_arn["resource_type"] = parsed_arn["service"]

        return cls(tenant, **parsed_arn)
