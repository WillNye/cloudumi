import gzip
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from botocore.exceptions import ClientError

from common.config import config
from common.exceptions.exceptions import (
    DataNotRetrievable,
    ExpiredData,
    UnsupportedRedisDataType,
)
from common.lib.asyncio import aio_wrapper, run_in_parallel
from common.lib.noq_json import SetEncoder
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.s3_helpers import get_object, put_object

# TODO: Assume role to S3 based on tenant Prefix
# We need to optionally perform nested assume-role calls. On the last assume-role call, we need to pass in a session
# policy that restricts S3 access to the tenant's prefix
# Ex: https://awsfeed.com/whats-new/security/implement-tenant-isolation-for-amazon-s3-and-aurora-postgresql-by-using-abac


async def store_json_results_in_redis_and_s3(
    data: Union[
        Dict[str, set],
        Dict[str, str],
        List[
            Union[
                Dict[str, Union[Union[str, int], Any]],
                Dict[str, Union[Union[str, None, int], Any]],
            ]
        ],
        str,
        Dict[str, list],
    ],
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
    json_encoder=None,
    s3_expires: int = None,
    tenant: str = None,
    redis_field: str = None,
):
    """
    Stores data in Redis and S3, depending on configuration

    :param s3_expires: Epoch time integer for when the written S3 object should expire
    :param redis_data_type: "str" or "hash", depending on how we're storing data in Redis
    :param data: Python dictionary or list that will be encoded in JSON for storage
    :param redis_key: Redis Key to store data to
    :param s3_bucket: S3 bucket to store data
    :param s3_key: S3 key to store data
    :return:
    """
    if not tenant:
        raise Exception("Invalid tenant")
    red = RedisHandler().redis_sync(tenant)
    stats = get_plugin_by_name(
        config.get("_global_.plugins.metrics", "cmsaas_metrics")
    )()

    last_updated_redis_key = config.get_tenant_specific_key(
        "store_json_results_in_redis_and_s3.last_updated_redis_key",
        tenant,
        f"{tenant}_STORE_JSON_RESULTS_IN_REDIS_AND_S3_LAST_UPDATED",
    )

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    last_updated = int(time.time())

    stats.count(
        f"{function}.called",
        tags={
            "redis_key": redis_key,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "tenant": tenant,
        },
    )

    # Force prefixing by tenant
    if s3_key:
        s3_key = f"{tenant}/{s3_key}"

    # If we've defined an S3 key, but not a bucket, let's use the default bucket if it's defined in configuration.
    if s3_key and not s3_bucket:
        s3_bucket = config.get_tenant_specific_key(
            "s3_cache_bucket",
            tenant,
            config.get("_global_.s3_cache_bucket"),
        )

    if redis_key:
        if redis_data_type == "str":
            if isinstance(data, str):
                red.set(redis_key, data)
            else:
                red.set(
                    redis_key, json.dumps(data, cls=SetEncoder, default=json_encoder)
                )
        elif redis_data_type == "hash":
            if data:
                if redis_field:
                    if isinstance(data, dict) or isinstance(data, list):
                        data_str = json.dumps(data)
                    else:
                        data_str = data
                    red.hset(redis_key, redis_field, data_str)
                else:
                    red.hset(redis_key, mapping=data)
        else:
            raise UnsupportedRedisDataType("Unsupported redis_data_type passed")
        red.hset(last_updated_redis_key, redis_key, last_updated)

    # TODO: If Redis field is defined, we should pull data from S3, update data, then store in S3.
    if s3_bucket and s3_key and not redis_field:
        s3_bucket_region: str = config.get(
            "_global_.s3_cache_bucket_region", config.region
        )
        s3_extra_kwargs = {}
        if isinstance(s3_expires, int):
            s3_extra_kwargs["Expires"] = datetime.utcfromtimestamp(s3_expires)
        data_for_s3 = json.dumps(
            {"last_updated": last_updated, "data": data},
            cls=SetEncoder,
            default=json_encoder,
            indent=2,
        ).encode()
        if s3_key.endswith(".gz"):
            data_for_s3 = gzip.compress(data_for_s3)

        put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=data_for_s3,
            tenant=tenant,
            region=s3_bucket_region,
            **s3_extra_kwargs,
        )


async def retrieve_json_data_from_redis_or_s3(
    redis_key: str = None,
    redis_data_type: str = "str",
    s3_bucket: str = None,
    s3_key: str = None,
    cache_to_redis_if_data_in_s3: bool = True,
    max_age: Optional[int] = None,
    default: Optional[Any] = None,
    json_object_hook: Optional[Any] = None,
    json_encoder: Optional[Any] = None,
    tenant: str = None,
    redis_field: str = None,  # Optional field for Redis hash
):
    """
    Retrieve data from Redis as a priority. If data is unavailable in Redis, fall back to S3 and attempt to store
    data in Redis for quicker retrieval later.

    :param redis_data_type: "str" or "hash", depending on how the data is stored in Redis
    :param redis_key: Redis Key to retrieve data from
    :param s3_bucket: S3 bucket to retrieve data from
    :param s3_key: S3 key to retrieve data from
    :param cache_to_redis_if_data_in_s3: Cache the data in Redis if the data is in S3 but not Redis
    :return:
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    last_updated_redis_key = config.get_tenant_specific_key(
        "store_json_results_in_redis_and_s3.last_updated_redis_key",
        tenant,
        f"{tenant}_STORE_JSON_RESULTS_IN_REDIS_AND_S3_LAST_UPDATED",
    )

    if not tenant:
        raise Exception("Invalid tenant")
    red = RedisHandler().redis_sync(tenant)
    stats = get_plugin_by_name(
        config.get("_global_.plugins.metrics", "cmsaas_metrics")
    )()
    stats.count(
        f"{function}.called",
        tags={
            "redis_key": redis_key,
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "tenant": tenant,
        },
    )
    s3_bucket_region: str = config.get("_global_.s3_cache_bucket_region", config.region)

    # Force prefixing by tenant
    if s3_key:
        s3_key = f"{tenant}/{s3_key}"

    # If we've defined an S3 key, but not a bucket, let's use the default bucket if it's defined in configuration.
    if s3_key and not s3_bucket:
        s3_bucket = config.get_tenant_specific_key(
            "s3_cache_bucket",
            tenant,
            config.get("_global_.s3_cache_bucket"),
        )

    data = None
    if redis_key:
        if redis_data_type == "str":
            data_s = red.get(redis_key)
            if data_s:
                data = json.loads(data_s, object_hook=json_object_hook)
        elif redis_data_type == "hash":
            if redis_field:
                data = red.hget(redis_key, redis_field)
            else:
                data = red.hgetall(redis_key)
        else:
            raise UnsupportedRedisDataType("Unsupported redis_data_type passed")
        if data and max_age:
            current_time = int(time.time())
            last_updated = int(red.hget(last_updated_redis_key, redis_key))
            if current_time - last_updated > max_age:
                data = None
                # Fall back to S3 if expired.
                if not s3_bucket or not s3_key:
                    raise ExpiredData(f"Data in Redis is older than {max_age} seconds.")

    # Fall back to S3 if there's no data
    if not data and s3_bucket and s3_key:
        try:
            s3_object = get_object(
                Bucket=s3_bucket, Key=s3_key, tenant=tenant, region=s3_bucket_region
            )
        except ClientError as e:
            if str(e) == (
                "An error occurred (NoSuchKey) when calling the GetObject operation: "
                "The specified key does not exist."
            ):
                if default is not None:
                    return default
            return data
        s3_object_content = await aio_wrapper(s3_object["Body"].read)
        if not s3_object_content and default is not None:
            return default
        if s3_key.endswith(".gz"):
            s3_object_content = gzip.decompress(s3_object_content)
        data_object = json.loads(s3_object_content, object_hook=json_object_hook)
        data = data_object["data"]

        if data and max_age:
            current_time = int(time.time())
            last_updated = data_object["last_updated"]
            if current_time - last_updated > max_age:
                raise ExpiredData(f"Data in S3 is older than {max_age} seconds.")
        if redis_key and cache_to_redis_if_data_in_s3:
            await store_json_results_in_redis_and_s3(
                data,
                redis_key=redis_key,
                redis_data_type=redis_data_type,
                json_encoder=json_encoder,
                tenant=tenant,
                redis_field=redis_field,
            )

    if data is not None:
        return data
    if default is not None:
        return default
    raise DataNotRetrievable("Unable to retrieve expected data.")


async def retrieve_json_data_from_s3_bulk(
    s3_bucket: str = None,
    s3_keys: Optional[List[str]] = None,
    max_age: Optional[int] = None,
    json_object_hook: Optional[Any] = None,
    json_encoder: Optional[Any] = None,
    tenant: str = None,
):
    """
    Retrieve data from multiple S3 keys in the same bucket, and combine the data. Useful for combining output of
    disparate resource caching functions (ex: combining the output of functions that determine IAM users on each of your
    accounts)

    :param s3_bucket: S3 bucket to retrieve data from
    :param s3_keys: S3 keys to retrieve data from
    :return:
    """
    if not tenant:
        raise Exception("No tenant specified")
    tasks = []
    for s3_key in s3_keys:
        # Force prefixing by tenant
        if s3_key:
            s3_key = f"{tenant}/{s3_key}"

        tasks.append(
            {
                "fn": retrieve_json_data_from_redis_or_s3,
                "kwargs": {
                    "s3_bucket": s3_bucket,
                    "s3_key": s3_key,
                    "max_age": max_age,
                    "json_object_hook": json_object_hook,
                    "json_encoder": json_encoder,
                    "tenant": tenant,
                },
            }
        )
    parallelized_task_results = await run_in_parallel(tasks, sync=False)

    all_function_results = []
    for parallelized_task_result in parallelized_task_results:
        all_function_results.append(parallelized_task_result["result"])
    results = []
    for result in all_function_results:
        results.extend(result)
    return results
