from datetime import datetime

from asgiref.sync import async_to_sync

import common.lib.noq_json as json
from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.redis import RedisHandler

# TODO: Get other resource types here


def cache_aws_resource_details(items, tenant):
    """
    Store all resource ARNs in Redis/S3. Items must have a TTL entry Used by typeahead endpoint.
    """
    redis_key = config.get_tenant_specific_key(
        "store_all_aws_resource_details.redis_key",
        tenant,
        f"{tenant}_ALL_AWS_RESOURCE_ARNS",
    )
    s3_bucket = config.get_tenant_specific_key(
        "all_aws_resource_details.s3.bucket", tenant
    )
    s3_key = config.get_tenant_specific_key(
        "all_aws_resource_details.s3.file",
        tenant,
        "all_aws_resource_details/all_aws_resource_details_v1.json.gz",
    )

    red = RedisHandler().redis_sync(tenant)

    existing_items = async_to_sync(retrieve_json_data_from_redis_or_s3)(
        redis_key=redis_key,
        redis_data_type="hash",
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
        default={},
    )
    items.update(existing_items)
    to_delete = []
    for arn, item in items.items():
        if isinstance(item, str):
            item = json.loads(item)
        if not item.get("ttl"):
            raise Exception("Item is missing TTL")
        if datetime.fromtimestamp(item["ttl"]) < datetime.utcnow():
            to_delete.append(arn)
        items[arn] = item
    for arn in to_delete:
        del items[arn]
    if to_delete:
        red.hdel(redis_key, *to_delete)

    for k, v in items.items():
        items[k] = json.dumps({"ttl": v["ttl"]})

    async_to_sync(store_json_results_in_redis_and_s3)(
        items,
        redis_key=redis_key,
        redis_data_type="hash",
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
    )


async def get_all_resource_arns(tenant):
    redis_key = config.get_tenant_specific_key(
        "store_all_aws_resource_details.redis_key",
        tenant,
        f"{tenant}_ALL_AWS_RESOURCE_ARNS",
    )
    s3_bucket = config.get_tenant_specific_key(
        "all_aws_resource_details.s3.bucket", tenant
    )
    s3_key = config.get_tenant_specific_key(
        "all_aws_resource_details.s3.file",
        tenant,
        "all_aws_resource_details/all_aws_resource_details_v1.json.gz",
    )

    items = await retrieve_json_data_from_redis_or_s3(
        redis_key=redis_key,
        redis_data_type="hash",
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
        default={},
    )
    return items.keys()
