from typing import Any, List

from common.aws.iam.role.models import IAMRole
from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.user_request.utils import get_active_tra_users_tag, get_tra_config


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


async def get_user_active_tra_roles_by_tag(tenant: str, user: str) -> list[str]:
    """Get active TRA roles for a given user

    :param tenant: The tenant to check against
    :param user:

    :return: A list of roles that can be used as part of the TRA workflow
    """
    from common.aws.utils import ResourceSummary, get_resource_tag
    from common.user_request.utils import TRA_CONFIG_BASE_KEY

    if not config.get_tenant_specific_key(
        f"{TRA_CONFIG_BASE_KEY}.enabled", tenant, False
    ):
        return []

    active_tra_roles = set()
    all_iam_roles = await IAMRole.query(tenant)
    tra_users_tag = get_active_tra_users_tag(tenant)
    base_tra_config = await get_tra_config(tenant=tenant)

    for iam_role in all_iam_roles:
        resource_summary = await ResourceSummary.set(tenant, iam_role.arn)
        tra_config = await get_tra_config(resource_summary, tra_config=base_tra_config)
        if not tra_config.enabled:
            continue

        if active_tra_users := get_resource_tag(
            iam_role.policy, tra_users_tag, True, set()
        ):
            if user in active_tra_users:
                active_tra_roles.add(iam_role.arn)

    return list(active_tra_roles)


async def get_tra_supported_roles_by_tag(
    eligible_roles: list[str], groups: list[str], tenant: str
) -> list[dict]:
    """Get TRA supported roles given a list of groups and already usable roles

    :param eligible_roles: Roles that are already accessible and can be ignored
    :param groups: List of groups to check against
    :param tenant: The tenant to check against

    :return: A list of roles that can be used as part of the TRA workflow
    """
    from common.aws.utils import ResourceSummary, get_resource_tag

    escalated_roles = dict()
    all_iam_roles = await IAMRole.query(tenant)
    base_tra_config = await get_tra_config(tenant=tenant)

    for iam_role in all_iam_roles:
        if iam_role.arn in eligible_roles:
            continue
        resource_summary = await ResourceSummary.set(tenant, iam_role.arn)
        tra_config = await get_tra_config(resource_summary, tra_config=base_tra_config)
        if not tra_config.enabled:
            continue

        role = iam_role.dict()
        if tra_groups := get_resource_tag(
            role, tra_config.supported_groups_tag, True, set()
        ):
            if any(group in tra_groups for group in groups):
                escalated_roles[iam_role.arn] = role

    return list(escalated_roles.values())
