import asyncio
import json
import time
from hashlib import sha1
from typing import Union

from common.aws.iam.role.models import IAMRole
from common.aws.utils import ResourceSummary, get_resource_tag
from common.config import config, models
from common.lib.assume_role import boto3_cached_conn
from common.lib.auth import is_tenant_admin
from common.models import (
    CloudCredentials,
    Command,
    ExtendedRequestModel,
    MfaSupport,
    PolicyRequestModificationRequestModel,
    TearAccountConfig,
    TearConfig,
    TearGroupConfig,
    TearRoleConfig,
)

log = config.get_logger(__name__)
TEAR_SUPPORT_TAG = "noq-tear-supported-groups"
TEAR_USERS_TAG = "noq-tear-active-users"


async def generate_dict_hash(dict_obj: dict) -> str:
    return sha1(
        json.dumps(dict_obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


async def update_extended_request_expiration_date(
    tenant: str, user: str, extended_request: ExtendedRequestModel, expiration_date: int
) -> ExtendedRequestModel:
    from common.lib.change_request import generate_policy_name, generate_policy_sid

    extended_request.expiration_date = expiration_date

    for change in extended_request.changes.changes:
        if change.change_type == "inline_policy":
            change.policy_name = await generate_policy_name(
                None, user, tenant, expiration_date
            )
        elif change.change_type in ["resource_policy", "sts_resource_policy"]:
            new_statement = []
            old_statement_hashes = []
            statements = change.policy.policy_document.get("Statement", [])

            if change.old_policy:
                old_statement_hashes = await asyncio.gather(
                    *[
                        generate_dict_hash(s)
                        for s in change.old_policy.policy_document.get("Statement", [])
                    ]
                )

            for statement in statements:
                if (
                    not old_statement_hashes
                    or not (await generate_dict_hash(statement)) in old_statement_hashes
                ):
                    statement["Sid"] = await generate_policy_sid(user, expiration_date)

                new_statement.append(statement)

            change.policy.policy_document["Statement"] = new_statement

    return extended_request


def get_change_arn(change) -> str:
    """Gets the ARN for a change dict or change model.
    The ARN for a change is different depending on the type of change it is.
    """
    if not isinstance(change, dict):
        try:
            change = change.dict()
        except Exception:
            raise TypeError(
                f"Expected change to be a Change model or of type dict; got {type(change)}"
            )

    if change["change_type"] not in [
        "resource_policy",
        "sts_resource_policy",
        "managed_policy",
    ]:
        if principal_arn := change.get("principal", {}).get("principal_arn", None):
            return principal_arn
    else:
        return change["arn"]


async def validate_custom_credentials(
    tenant: str,
    extended_request: ExtendedRequestModel,
    policy_request_model: PolicyRequestModificationRequestModel,
    cloud_credentials: CloudCredentials,
):
    modification_model = policy_request_model.modification_model
    if cloud_credentials and modification_model.command == Command.apply_change:
        if cloud_credentials.aws:
            try:
                sts = boto3_cached_conn(
                    "sts", tenant, None, custom_aws_credentials=cloud_credentials.aws
                )
                whoami = sts.get_caller_identity()
                custom_account = whoami["Account"]
            except Exception:
                raise ValueError("Invalid AWS credentials provided")
        else:
            raise ValueError("Only AWS credentials are supported at this time")

        change_arns = set()

        # Get all change arns
        for change in extended_request.changes.changes:
            if change.id != modification_model.change_id:
                continue

            if change_arn := get_change_arn(change):
                change_arns.add(change_arn)
            else:
                log.warning(
                    {"message": "ARN for change not found", "change": change.dict()}
                )

        resource_summaries = await asyncio.gather(
            *[ResourceSummary.set(tenant, arn) for arn in change_arns]
        )
        if invalid_resources := [
            rs for rs in resource_summaries if rs.account != custom_account
        ]:
            err_str = "\n".join(
                [
                    f"(Resource: {rs.arn}, Account: {rs.account})"
                    for rs in invalid_resources
                ]
            )
            raise ValueError(
                f"Resource(s) on a different account than the provided credentials. {err_str}"
            )


def mfa_enabled_for_config(tear_config):
    return bool(tear_config.mfa and tear_config.mfa.enabled)


def get_tear_config(
    tenant: str, account: str = None, role: str = None, user_groups: list[str] = None
) -> Union[TearConfig | TearRoleConfig | TearAccountConfig | TearGroupConfig]:
    """Retrieve the proper TEAR config based on provided account, role, and user groups with tear access to the role.
    Config priority:
        1: group
            1.a requires_approval=False
            1.b mfa_enabled=False
            1.c enabled=True
            1.d enabled=False
        2: role
        3: account
    """
    tear_config: TearConfig = (
        models.ModelAdapter(TearConfig)
        .load_config("temporary_elevated_access_requests", tenant)
        .model
    )
    if not tear_config:
        return TearConfig()  # Default config

    # Set defaults
    if not tear_config.mfa:
        tear_config.mfa = MfaSupport()
        # if mfa hasn't been explicitly set the default by checking if tenant has mfa support
        tear_config.mfa.enabled = bool(
            config.get_tenant_specific_key("secrets.mfa", tenant, False)
        )
    tear_config.supported_groups_tag = get_tear_supported_groups_tag(tenant)
    tear_config.active_users_tag = get_active_tear_users_tag(tenant)

    if not tear_config.custom_configs:
        return tear_config

    config_attrs = [
        "requires_approval",
        "enabled",
        "mfa",
    ]
    custom_tear_config = None

    if user_groups and (tear_groups := tear_config.custom_configs.group_configs):
        # In the event the user is part of multiple groups with TEAR access the group requiring the least auth is used
        # Currently, this is the order from highest to lowest priority:
        # requires_approval=False, mfa_enabled=False, enabled=True, enabled=False
        tear_group_map = {tear_group.name: tear_group for tear_group in tear_groups}
        for user_group in user_groups:
            tear_group = tear_group_map.get(user_group)
            if not tear_group:
                continue
            elif (
                custom_tear_config
                and custom_tear_config.enabled
                and not tear_group.enabled
            ):
                continue
            elif not tear_group.requires_approval:
                custom_tear_config = tear_group
                break
            elif not custom_tear_config:
                custom_tear_config = tear_group
            elif mfa_enabled_for_config(
                custom_tear_config
            ) and not mfa_enabled_for_config(tear_group):
                custom_tear_config = tear_group
            elif tear_group.enabled and not custom_tear_config.enabled:
                custom_tear_config = tear_group

    if (
        role
        and not custom_tear_config
        and (tear_roles := tear_config.custom_configs.role_configs)
    ):
        for tear_role in tear_roles:
            if role == tear_role.name:
                custom_tear_config = tear_role
                break

    if (
        account
        and not custom_tear_config
        and (tear_accounts := tear_config.custom_configs.account_configs)
    ):
        for tear_account in tear_accounts:
            if account == tear_account.id and tear_account.enabled:
                custom_tear_config = tear_account
                break

    if custom_tear_config:
        # Tags are set globally so set the tags for the custom config
        custom_tear_config.active_users_tag = tear_config.active_users_tag
        custom_tear_config.supported_groups_tag = tear_config.supported_groups_tag

        # Use the parent (tear_config) as the default for attributes that weren't set.
        for config_attr in config_attrs:
            if getattr(custom_tear_config, config_attr, None) is None:
                parent_val = getattr(tear_config, config_attr, None)
                setattr(custom_tear_config, config_attr, parent_val)
        return custom_tear_config

    return tear_config


def get_user_tear_groups_for_role(
    tenant: str, iam_role: IAMRole, user_groups: list[str]
):
    role_tear_tags = get_resource_tag(
        iam_role.policy, get_tear_supported_groups_tag(tenant), default=[]
    )
    return [user_group for user_group in user_groups if user_group in role_tear_tags]


async def get_tear_config_for_request(
    tenant: str, arn: str, user_groups: list[str]
) -> Union[TearConfig | TearRoleConfig | TearAccountConfig | TearGroupConfig]:
    resource_summary = await ResourceSummary.set(tenant, arn)
    iam_role = await IAMRole.get(tenant, resource_summary.account, resource_summary.arn)
    tear_groups = get_user_tear_groups_for_role(tenant, iam_role, user_groups)
    return get_tear_config(
        tenant, resource_summary.account, resource_summary.name, tear_groups
    )


def get_active_tear_users_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        "temporary_elevated_access_requests.active_users_tag", tenant, TEAR_USERS_TAG
    )


def get_tear_supported_groups_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        "temporary_elevated_access_requests.supported_groups_tag",
        tenant,
        TEAR_SUPPORT_TAG,
    )


async def can_approve_reject_request(user, secondary_approvers, groups, tenant):
    # Allow admins to approve and reject all requests
    if is_tenant_admin(user, groups, tenant):
        return True

    if secondary_approvers:
        for g in secondary_approvers:
            if g in groups or g == user:
                return True
    return False


async def can_cancel_request(current_user, requesting_user, groups, tenant):
    # Allow the requesting user to cancel their own request
    if current_user == requesting_user:
        return True

    # Allow admins to cancel requests
    if is_tenant_admin(current_user, groups, tenant):
        return True

    # Allow restricted admins to cancel requests
    for g in config.get_tenant_specific_key("groups.can_admin_restricted", tenant):
        if g in groups:
            return True

    return False


async def can_move_back_to_pending(current_user, request, groups, tenant):
    # Don't allow returning requests to pending state if more than a day has passed since the last update
    if request.get("last_updated", 0) < int(time.time()) - 86400:
        return False
    # Allow admins to return requests back to pending state
    if is_tenant_admin(current_user, groups, tenant):
        return True
    return False


def get_pending_requests_url(tenant):
    return f"{config.get_tenant_specific_key('url', tenant)}/accessui/pending"


def get_request_review_url(request_id: str, tenant: str) -> str:
    return (
        f"{config.get_tenant_specific_key('url', tenant)}/accessui/request/{request_id}"
    )


def get_accessui_pending_requests_url(tenant):
    return f"{config.get_tenant_specific_key('accessui_url', tenant)}/requests"


def get_accessui_request_review_url(request_id, tenant):
    return f"{config.get_tenant_specific_key('accessui_url', tenant)}/requests/{request_id}"
