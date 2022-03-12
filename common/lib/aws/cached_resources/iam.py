from typing import Any, List

from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)


async def store_iam_roles_for_host(all_roles: Any, host: str) -> bool:
    await store_json_results_in_redis_and_s3(
        all_roles,
        redis_key=config.get_host_specific_key(
            "aws.iamroles_redis_key",
            host,
            f"{host}_IAM_ROLE_CACHE",
        ),
        redis_data_type="hash",
        s3_bucket=config.get_host_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket",
            host,
        ),
        s3_key=config.get_host_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            host,
            "account_resource_cache/cache_all_roles_v1.json.gz",
        ),
        host=host,
    )
    return True


async def retrieve_iam_roles_for_host(host: str):
    return await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get_host_specific_key(
            "aws.iamroles_redis_key",
            host,
            f"{host}_IAM_ROLE_CACHE",
        ),
        redis_data_type="hash",
        s3_bucket=config.get_host_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.bucket",
            host,
        ),
        s3_key=config.get_host_specific_key(
            "cache_iam_resources_across_accounts.all_roles_combined.s3.file",
            host,
            "account_resource_cache/cache_all_roles_v1.json.gz",
        ),
        default={},
        host=host,
    )


async def get_identity_arns_for_account(
    host: str, account_id: str, identity_type: str = "role"
) -> List[str]:
    if identity_type != "role":
        raise NotImplementedError(f"identity_type {identity_type} not implemented")

    all_roles = await retrieve_iam_roles_for_host(host)
    matching_roles = set()
    for arn in all_roles.keys():
        if arn.split(":")[4] == account_id:
            matching_roles.add(arn)
    return list(matching_roles)


async def store_iam_managed_policies_for_host(
    host: str, iam_policies: Any, account_id: str
) -> bool:
    await store_json_results_in_redis_and_s3(
        iam_policies,
        s3_bucket=config.get_host_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.bucket",
            host,
        ),
        s3_key=config.get_host_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.file",
            host,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="iam_policies", account_id=account_id),
        host=host,
    )


async def retrieve_iam_managed_policies_for_host(host: str, account_id: str) -> bool:
    managed_policies = await retrieve_json_data_from_redis_or_s3(
        s3_bucket=config.get_host_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.bucket",
            host,
        ),
        s3_key=config.get_host_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.file",
            host,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="iam_policies", account_id=account_id),
        host=host,
    )
    formatted_policies = {}
    for policy in managed_policies:
        for policy_version in policy.get("PolicyVersionList", []):
            if policy_version.get("IsDefaultVersion", False):
                formatted_policies[policy["PolicyName"]] = policy_version.get(
                    "Document", {}
                )
                break
    return formatted_policies
