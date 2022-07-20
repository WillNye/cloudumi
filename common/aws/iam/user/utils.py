import asyncio
import sys
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from common.aws.iam.utils import _cloudaux_to_aws, get_tenant_iam_conn
from common.config import config
from common.config.models import ModelAdapter
from common.lib.asyncio import aio_wrapper
from common.lib.plugins import get_plugin_by_name
from common.models import SpokeAccount

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


def _get_iam_user_sync(account_id, user_name, conn, tenant) -> Optional[Dict[str, Any]]:
    from common.aws.iam.policy.utils import (
        get_user_inline_policies,
        get_user_managed_policies,
    )

    client = get_tenant_iam_conn(tenant, account_id, "noq_get_iam_user", read_only=True)
    user = client.get_user(UserName=user_name)["User"]
    user["ManagedPolicies"] = get_user_managed_policies({"UserName": user_name}, **conn)
    user["InlinePolicies"] = get_user_inline_policies({"UserName": user_name}, **conn)
    user["Tags"] = client.list_user_tags(UserName=user_name)
    user["Groups"] = client.list_groups_for_user(UserName=user_name)
    return user


async def _get_iam_user_async(
    account_id, user_name, conn, tenant
) -> Optional[Dict[str, Any]]:
    from common.aws.iam.policy.utils import (
        get_user_inline_policies,
        get_user_managed_policies,
    )

    tasks = []
    client = await aio_wrapper(
        get_tenant_iam_conn,
        tenant,
        account_id,
        "noq_get_iam_user",
        read_only=True,
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
                aio_wrapper(t, {"UserName": user_name}, tenant=tenant, **conn)
            )
        )

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
    user["Groups"] = async_task_result[3].get("Groups", [])
    return user


async def fetch_iam_user(
    account_id: str,
    user_arn: str,
    tenant: str,
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
        "tenant": tenant,
    }

    try:
        user_name = user_arn.split("/")[-1]
        conn = {
            "account_number": account_id,
            "assume_role": ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_id})
            .first.name,
            "region": config.region,
            "client_kwargs": config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
        }
        if run_sync:
            user = _get_iam_user_sync(account_id, user_name, conn, tenant)
        else:
            user = await _get_iam_user_async(account_id, user_name, conn, tenant)

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
                    "tenant": tenant,
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
                    "tenant": tenant,
                },
            )
            raise
    await _cloudaux_to_aws(user)
    return user
