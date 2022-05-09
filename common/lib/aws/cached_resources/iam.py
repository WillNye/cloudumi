from typing import Any, List

from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)


async def store_iam_roles_for_host(all_roles: Any, host: str) -> bool:
    """Store all IAM roles for a host in Redis and S3.

    :param all_roles: A dict of all IAM roles for a host
    :param host: Tenant ID
    :return: bool indicating success
    """
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


async def get_iam_roles_for_host(host: str) -> Any:
    """Retrieves all IAM roles for a host from Redis or S3.

    :param host: Tenant ID
    :return: Any (A struct with all of the IAM roles)
    """
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
    """Retrieves a list of all IAM role ARNs for a given account.

    :param host: Tenant ID
    :param account_id: AWS Account ID
    :param identity_type: "user" (indicating AWS IAM User) or "role" (Indicating AWS IAM Role), defaults to "role"
    :raises NotImplementedError: When identity type is not supported
    :return: _description_
    """
    if identity_type != "role":
        raise NotImplementedError(f"identity_type {identity_type} not implemented")

    all_roles = await get_iam_roles_for_host(host)
    matching_roles = set()
    for arn in all_roles.keys():
        if ":role/service-role/" in arn:
            continue
        if arn.split(":")[4] == account_id:
            matching_roles.add(arn)
    return list(matching_roles)


async def store_iam_managed_policies_for_host(
    host: str, iam_policies: Any, account_id: str
) -> bool:
    """Store all managed policies for an account in S3.

    :param host: Tenant ID
    :param iam_policies: A struct containing all managed policies for an account
    :param account_id: AWS Account ID
    :return: A boolean indicating success
    """
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
    return True


async def retrieve_iam_managed_policies_for_host(host: str, account_id: str) -> bool:
    """
    Retrieves all managed policies for an account from S3
    """
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
