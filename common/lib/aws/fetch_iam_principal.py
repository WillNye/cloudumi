import asyncio
import copy
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import ujson as json
from botocore.exceptions import ClientError
from retrying import retry

from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.iam import (
    get_role_inline_policies,
    get_role_managed_policies,
    get_user_inline_policies,
    get_user_managed_policies,
    list_role_tags,
)
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.dynamo import IAMRoleDynamoHandler
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.terraform.transformers.IAMRoleTransformer import IAMRoleTransformer
from common.models import SpokeAccount

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _fetch_role_from_redis(role_arn: str, host: str):
    """Fetch the role from redis with a retry.

    :param role_arn:
    :return:
    """
    redis_key = config.get_host_specific_key(
        "aws.iamroles_redis_key",
        host,
        f"{host}_IAM_ROLE_CACHE",
    )
    red = RedisHandler().redis_sync(host)
    return red.hget(redis_key, role_arn)


@retry(
    stop_max_attempt_number=3,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _add_role_to_redis(role_entry: dict, host: str):
    """Add the role to redis with a retry.

    :param role_entry:
    :return:
    """
    redis_key = config.get_host_specific_key(
        "aws.iamroles_redis_key",
        host,
        f"{host}_IAM_ROLE_CACHE",
    )
    red = RedisHandler().redis_sync(host)
    red.hset(redis_key, role_entry["arn"], json.dumps(role_entry))


async def _cloudaux_to_aws(principal):
    """Convert the cloudaux get_role/get_user into the get_account_authorization_details equivalent."""
    # Pop out the fields that are not required:
    # Arn and RoleName/UserName will be popped off later:
    unrequired_fields = ["_version", "MaxSessionDuration"]
    principal_type = principal["Arn"].split(":")[-1].split("/")[0]
    for uf in unrequired_fields:
        principal.pop(uf, None)

    # Fix the Managed Policies:
    principal["AttachedManagedPolicies"] = list(
        map(
            lambda x: {"PolicyName": x["name"], "PolicyArn": x["arn"]},
            principal.get("ManagedPolicies", []),
        )
    )
    principal.pop("ManagedPolicies", None)

    # Fix the tags:
    if isinstance(principal.get("Tags", {}), dict):
        principal["Tags"] = list(
            map(
                lambda key: {"Key": key, "Value": principal["Tags"][key]},
                principal.get("Tags", {}),
            )
        )

    # Note: the instance profile list is verbose -- not transforming it (outside of renaming the field)!
    principal["InstanceProfileList"] = principal.pop("InstanceProfiles", [])

    # Inline Policies:
    if principal_type == "role":

        principal["RolePolicyList"] = list(
            map(
                lambda name: {
                    "PolicyName": name,
                    "PolicyDocument": principal["InlinePolicies"][name],
                },
                principal.get("InlinePolicies", {}),
            )
        )
    else:
        principal["UserPolicyList"] = copy.deepcopy(principal.pop("InlinePolicies", []))
    principal.pop("InlinePolicies", None)

    return principal


def _get_iam_role_sync(
    account_id, role_name, conn, host: str
) -> Optional[Dict[str, Any]]:
    client = boto3_cached_conn(
        "iam",
        host,
        None,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        session_name=sanitize_session_name("consoleme_get_iam_role"),
    )
    role = client.get_role(RoleName=role_name)["Role"]
    role["ManagedPolicies"] = get_role_managed_policies(
        {"RoleName": role_name}, host=host, **conn
    )
    role["InlinePolicies"] = get_role_inline_policies(
        {"RoleName": role_name}, host=host, **conn
    )
    role["Tags"] = list_role_tags({"RoleName": role_name}, host=host, **conn)
    return role


async def _get_iam_role_async(
    account_id, role_name, conn, host: str
) -> Optional[Dict[str, Any]]:
    tasks = []
    client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        host,
        None,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )
    role_details = asyncio.ensure_future(
        aio_wrapper(client.get_role, RoleName=role_name)
    )
    tasks.append(role_details)
    # executor = ThreadPoolExecutor(max_workers=os.cpu_count())
    # futures = []
    # all_tasks = [
    #     get_role_managed_policies,
    #     get_role_inline_policies,
    #     list_role_tags,
    # ]

    import concurrent.futures

    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=4,
    )
    import functools

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(
            executor, functools.partial(client.get_role, RoleName=role_name)
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                get_role_managed_policies, {"RoleName": role_name}, host=host, **conn
            ),
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                get_role_inline_policies, {"RoleName": role_name}, host=host, **conn
            ),
        ),
        loop.run_in_executor(
            executor,
            functools.partial(
                list_role_tags, {"RoleName": role_name}, host=host, **conn
            ),
        ),
    ]
    # completed, pending = await asyncio.wait(tasks)
    # results = [t.result() for t in completed]
    results = await asyncio.gather(*tasks)
    # results = await run_io_tasks_in_parallel_v2(executor, [
    #     lambda: {"Role": client.get_role(RoleName=role_name)},
    #     lambda: {"ManagedPolicies": get_role_managed_policies({"RoleName": role_name}, host=host, **conn)},
    #     lambda: {"InlinePolicies": get_role_inline_policies({"RoleName": role_name}, host=host, **conn)},
    #     lambda: {"Tags": list_role_tags({"RoleName": role_name}, host=host, **conn)}]
    #
    # )

    role = results[0]["Role"]
    role["ManagedPolicies"] = results[1]
    role["InlinePolicies"] = results[2]
    role["Tags"] = results[3]

    # role = {}
    #
    # for d in results:
    #     if d.get("Role"):
    #         role.update(d["Role"]["Role"])
    #     else:
    #         role.update(d)

    return role


async def fetch_iam_role(
    account_id: str,
    role_arn: str,
    host: str,
    force_refresh: bool = False,
    run_sync=False,
) -> Optional[Dict[str, Any]]:
    """Fetch the IAM Role template from Redis and/or Dynamo.

    :param account_id:
    :param role_arn:
    :return:
    """
    from common.lib.aws.utils import get_aws_principal_owner

    log_data: dict = {
        "function": f"{sys._getframe().f_code.co_name}",
        "role_arn": role_arn,
        "account_id": account_id,
        "force_refresh": force_refresh,
        "host": host,
    }
    dynamo = IAMRoleDynamoHandler(host)

    red = RedisHandler().redis_sync(host)

    result: dict = {}

    if not force_refresh:
        # First check redis:
        result: str = await aio_wrapper(_fetch_role_from_redis, role_arn, host)

        if result:
            result: dict = json.loads(result)

            # If this item is less than an hour old, then return it from Redis.
            if result["ttl"] > int(
                (datetime.utcnow() - timedelta(hours=1)).timestamp()
            ):
                log_data["message"] = "Returning role from Redis."
                log.debug(log_data)
                stats.count(
                    "aws.fetch_iam_role.in_redis",
                    tags={
                        "account_id": account_id,
                        "role_arn": role_arn,
                        "host": host,
                    },
                )
                result["policy"] = json.loads(result["policy"])
                return result

        # If not in Redis or it's older than an hour, proceed to DynamoDB:
        result = await aio_wrapper(dynamo.fetch_iam_role, role_arn, host)

    # If it's NOT in dynamo, or if we're forcing a refresh, we need to reach out to AWS and fetch:
    if force_refresh or not result.get("Item"):
        if force_refresh:
            log_data["message"] = "Force refresh is enabled. Going out to AWS."
            stats.count(
                "aws.fetch_iam_role.force_refresh",
                tags={
                    "account_id": account_id,
                    "role_arn": role_arn,
                    "host": host,
                },
            )
        else:
            log_data["message"] = "Role is missing in DDB. Going out to AWS."
            stats.count(
                "aws.fetch_iam_role.missing_dynamo",
                tags={
                    "account_id": account_id,
                    "role_arn": role_arn,
                    "host": host,
                },
            )
        log.debug(log_data)
        try:
            role_name = role_arn.split("/")[-1]
            conn = {
                "account_number": account_id,
                "assume_role": ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", host)
                .with_query({"account_id": account_id})
                .first.name,
                "region": config.region,
                "client_kwargs": config.get_host_specific_key(
                    "boto3.client_kwargs", host, {}
                ),
            }
            if run_sync:
                role = _get_iam_role_sync(account_id, role_name, conn, host)
            else:
                role = await _get_iam_role_async(account_id, role_name, conn, host)

        except ClientError as ce:
            if ce.response["Error"]["Code"] == "NoSuchEntity":
                # The role does not exist:
                log_data["message"] = "Role does not exist in AWS."
                log.error(log_data)
                stats.count(
                    "aws.fetch_iam_role.missing_in_aws",
                    tags={
                        "account_id": account_id,
                        "role_arn": role_arn,
                        "host": host,
                    },
                )
                return None

            else:
                log_data["message"] = f"Some other error: {ce.response}"
                log.error(log_data)
                stats.count(
                    "aws.fetch_iam_role.aws_connection_problem",
                    tags={
                        "account_id": account_id,
                        "role_arn": role_arn,
                        "host": host,
                    },
                )
                raise

        # Format the role for DynamoDB and Redis:
        await _cloudaux_to_aws(role)
        iam_role_transformer = IAMRoleTransformer(role)
        terraformed_role = iam_role_transformer._generate_hcl2_code(role)
        last_updated: int = int((datetime.utcnow()).timestamp())
        result = {
            "arn": role.get("Arn"),
            "host": host,
            "name": role.pop("RoleName"),
            "resourceId": role.pop("RoleId"),
            "accountId": account_id,
            "tags": role.get("Tags", []),
            "policy": dynamo.convert_iam_resource_to_json(role),
            "permissions_boundary": role.get("PermissionsBoundary", {}),
            "owner": get_aws_principal_owner(role, host),
            "templated": red.hget(
                config.get_host_specific_key(
                    "templated_roles.redis_key",
                    host,
                    f"{host}_TEMPLATED_ROLES_v2",
                ),
                role.get("Arn").lower(),
            ),
            "last_updated": last_updated,
            "terraformed_role": terraformed_role,
            "ttl": int((datetime.utcnow() + timedelta(hours=6)).timestamp()),
        }

        # Sync with DDB:
        await aio_wrapper(dynamo.sync_iam_role_for_account, result)
        log_data["message"] = "Role fetched from AWS, and synced with DDB."
        stats.count(
            "aws.fetch_iam_role.fetched_from_aws",
            tags={
                "account_id": account_id,
                "role_arn": role_arn,
                "host": host,
            },
        )

    else:
        log_data["message"] = "Role fetched from DDB."
        stats.count(
            "aws.fetch_iam_role.in_dynamo",
            tags={
                "account_id": account_id,
                "role_arn": role_arn,
                "host": host,
            },
        )

        # Fix the TTL:
        result["Item"]["ttl"] = int(result["Item"]["ttl"])
        result = result["Item"]

    # Update the redis cache:
    stats.count(
        "aws.fetch_iam_role.in_dynamo",
        tags={
            "account_id": account_id,
            "role_arn": role_arn,
            "host": host,
        },
    )
    await aio_wrapper(_add_role_to_redis, result, host)

    log_data["message"] += " Updated Redis."
    log.debug(log_data)

    result["policy"] = json.loads(result["policy"])
    return result


def _get_iam_user_sync(account_id, user_name, conn, host) -> Optional[Dict[str, Any]]:
    client = boto3_cached_conn(
        "iam",
        host,
        user_name,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        session_name=sanitize_session_name("consoleme_get_iam_user"),
    )
    user = client.get_user(UserName=user_name)["User"]
    user["ManagedPolicies"] = get_user_managed_policies({"UserName": user_name}, **conn)
    user["InlinePolicies"] = get_user_inline_policies({"UserName": user_name}, **conn)
    user["Tags"] = client.list_user_tags(UserName=user_name)
    user["Groups"] = client.list_groups_for_user(UserName=user_name)
    return user


async def _get_iam_user_async(
    account_id, user_name, conn, host
) -> Optional[Dict[str, Any]]:
    tasks = []
    client = await aio_wrapper(
        boto3_cached_conn,
        "iam",
        host,
        user_name,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        read_only=True,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )
    user_details = asyncio.ensure_future(
        aio_wrapper(client.get_user, UserName=user_name)
    )
    tasks.append(user_details)

    all_tasks = [
        get_user_managed_policies,
        get_user_inline_policies,
    ]

    for t in all_tasks:
        tasks.append(
            asyncio.ensure_future(
                aio_wrapper(t, {"UserName": user_name}, host=host, **conn)
            )
        )

    user_tag_details = asyncio.ensure_future(
        aio_wrapper(client.list_user_tags, UserName=user_name)
    )
    tasks.append(user_tag_details)

    user_group_details = asyncio.ensure_future(
        aio_wrapper(client.list_groups_for_user, UserName=user_name)
    )
    tasks.append(user_group_details)

    responses = asyncio.gather(*tasks)
    async_task_result = await responses
    user = async_task_result[0]["User"]
    user["ManagedPolicies"] = async_task_result[1]
    inline_policies = []
    for name, policy in async_task_result[2].items():
        inline_policies.append({"PolicyName": name, "PolicyDocument": policy})
    user["InlinePolicies"] = inline_policies
    user["Tags"] = async_task_result[3].get("Tags", [])
    user["Groups"] = async_task_result[4].get("Groups", [])
    return user


async def fetch_iam_user(
    account_id: str,
    user_arn: str,
    host: str,
    run_sync=False,
) -> Optional[Dict[str, Any]]:
    """Fetch the IAM User from AWS in threadpool if run_sync=False, otherwise synchronously.

    :param account_id:
    :param user_arn:
    :return:
    """
    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user_arn": user_arn,
        "account_id": account_id,
        "host": host,
    }

    try:
        user_name = user_arn.split("/")[-1]
        conn = {
            "account_number": account_id,
            "assume_role": ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            "region": config.region,
            "client_kwargs": config.get_host_specific_key(
                "boto3.client_kwargs", host, {}
            ),
        }
        if run_sync:
            user = _get_iam_user_sync(account_id, user_name, conn, host)
        else:
            user = await _get_iam_user_async(account_id, user_name, conn, host)

    except ClientError as ce:
        if ce.response["Error"]["Code"] == "NoSuchEntity":
            # The user does not exist:
            log_data["message"] = "User does not exist in AWS."
            log.error(log_data)
            stats.count(
                "aws.fetch_iam_user.missing_in_aws",
                tags={
                    "account_id": account_id,
                    "user_arn": user_arn,
                    "host": host,
                },
            )
            return None

        else:
            log_data["message"] = f"Some other error: {ce.response}"
            log.error(log_data)
            stats.count(
                "aws.fetch_iam_user.aws_connection_problem",
                tags={
                    "account_id": account_id,
                    "user_arn": user_arn,
                    "host": host,
                },
            )
            raise
    await _cloudaux_to_aws(user)
    return user
