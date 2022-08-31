from typing import Any, List

from common.aws.iam.role.models import IAMRole
from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.user_request.utils import get_active_tear_users_tag, get_tear_config


async def get_identity_arns_for_account(
    tenant: str, account_id: str, identity_type: str = "role"
) -> List[str]:
    """Retrieves a list of all IAM role ARNs for a given account.

    :param tenant: Tenant ID
    :param account_id: AWS Account ID
    :param identity_type: "user" (indicating AWS IAM User) or "role" (Indicating AWS IAM Role), defaults to "role"
    :raises NotImplementedError: When identity type is not supported
    :return: _description_
    """
    if identity_type != "role":
        raise NotImplementedError(f"identity_type {identity_type} not implemented")

    all_roles = await IAMRole.query(tenant, attributes_to_get=["arn"])
    matching_roles = set()
    for role in all_roles:
        if ":role/service-role/" in role.arn:
            continue
        if role.arn.split(":")[4] == account_id:
            matching_roles.add(role.arn)
    return list(matching_roles)


async def store_iam_managed_policies_for_tenant(
    tenant: str, iam_policies: Any, account_id: str
) -> bool:
    """Store all managed policies for an account in S3.

    :param tenant: Tenant ID
    :param iam_policies: A struct containing all managed policies for an account
    :param account_id: AWS Account ID
    :return: A boolean indicating success
    """
    await store_json_results_in_redis_and_s3(
        iam_policies,
        s3_bucket=config.get_tenant_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.bucket",
            tenant,
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="iam_policies", account_id=account_id),
        tenant=tenant,
    )
    return True


async def retrieve_iam_managed_policies_for_tenant(
    tenant: str, account_id: str
) -> bool:
    """
    Retrieves all managed policies for an account from S3
    """
    managed_policies = await retrieve_json_data_from_redis_or_s3(
        s3_bucket=config.get_tenant_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.bucket",
            tenant,
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_iam_resources_for_account.iam_policies.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="iam_policies", account_id=account_id),
        tenant=tenant,
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


async def get_user_active_tear_roles_by_tag(tenant: str, user: str) -> list[str]:
    """Get active TEAR roles for a given user

    :param tenant: The tenant to check against
    :param user:

    :return: A list of roles that can be used as part of the TEAR workflow
    """
    from common.aws.utils import ResourceSummary, get_resource_tag

    if not config.get_tenant_specific_key(
        "temporary_elevated_access_requests.enabled", tenant, False
    ):
        return []

    active_tear_roles = set()
    all_iam_roles = await IAMRole.query(tenant)
    tear_users_tag = get_active_tear_users_tag(tenant)

    for iam_role in all_iam_roles:
        resource_summary = await ResourceSummary.set(tenant, iam_role.arn)
        tear_config = get_tear_config(resource_summary)
        if not tear_config.enabled:
            continue

        if active_tear_users := get_resource_tag(
            iam_role.policy, tear_users_tag, True, set()
        ):
            if user in active_tear_users:
                active_tear_roles.add(iam_role.arn)

    return list(active_tear_roles)


async def get_tear_supported_roles_by_tag(
    eligible_roles: list[str], groups: list[str], tenant: str
) -> list[dict]:
    """Get TEAR supported roles given a list of groups and already usable roles

    :param eligible_roles: Roles that are already accessible and can be ignored
    :param groups: List of groups to check against
    :param tenant: The tenant to check against

    :return: A list of roles that can be used as part of the TEAR workflow
    """
    from common.aws.utils import ResourceSummary, get_resource_tag

    escalated_roles = dict()
    all_iam_roles = await IAMRole.query(tenant)

    for iam_role in all_iam_roles:
        if iam_role.arn in eligible_roles:
            continue
        resource_summary = await ResourceSummary.set(tenant, iam_role.arn)
        tear_config = get_tear_config(resource_summary)
        if not tear_config.enabled:
            continue

        role = iam_role.dict()
        if tear_groups := get_resource_tag(
            role, tear_config.supported_groups_tag, True, set()
        ):
            if any(group in tear_groups for group in groups):
                escalated_roles[iam_role.arn] = role

    return list(escalated_roles.values())
