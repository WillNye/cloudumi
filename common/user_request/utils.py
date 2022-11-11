import asyncio
import json
import re
import time
from datetime import datetime, timezone
from hashlib import sha1
from typing import get_args, get_type_hints

from dateutil import parser

from common.aws.iam.role.models import IAMRole
from common.aws.utils import ResourceSummary, get_resource_tag
from common.config import config, models
from common.lib.assume_role import boto3_cached_conn
from common.lib.auth import is_tenant_admin
from common.lib.timeout import Timeout
from common.models import (
    ChangeModelArray,
    CloudCredentials,
    Command,
    ExtendedRequestModel,
    MfaSupport,
    PolicyRequestModificationRequestModel,
    TraConfig,
)

log = config.get_logger(__name__)
TRA_SUPPORT_TAG = "noq-tra-supported-groups"
TRA_USERS_TAG = "noq-tra-active-users"
TRA_CONFIG_BASE_KEY = "temporary_role_access_requests"


class ChangeValidator:
    _change_types = set()

    @classmethod
    def change_types(cls):
        if not cls._change_types:
            # Change type hint is List[Union[ChangeTypes...]]
            # Parse that out to get all supported change types
            change_list_hint = get_type_hints(ChangeModelArray)["changes"]
            change_models = get_args(get_args(change_list_hint)[0])
            for change_model in change_models:
                change_type_field = change_model.__dict__["__fields__"]["change_type"]
                cls._change_types.add(
                    change_model.get_field_type(change_type_field).__dict__["regex"]
                )

        return cls._change_types

    @classmethod
    def is_valid(cls, change_type: str) -> bool:
        return any(
            re.match(change_type_re, change_type)
            for change_type_re in cls.change_types()
        )


def normalize_expiration_date(request):
    if expiration_date := getattr(request, "expiration_date", None):
        if isinstance(expiration_date, str):
            expiration_date = parser.parse(expiration_date)
        if utc_offset := expiration_date.utcoffset():
            expiration_date -= utc_offset
        request.expiration_date = expiration_date.replace(tzinfo=timezone.utc)

    return request


def get_expiry_sid_str(dt_obj: datetime) -> str:
    return dt_obj.strftime("%Y%m%d_%H%M%S")


def re_match_any_pattern(str_obj: str, regex_patterns: list[str]) -> bool:
    if str_obj == "*" or any(regex == "*" for regex in regex_patterns):
        return True

    try:
        with Timeout(seconds=5):
            return any(re.match(regex, str_obj) for regex in regex_patterns)
    except TimeoutError as err:
        log.critical(
            {
                "error": str(err),
                "message": "regex timed out",
                "regex_patterns": regex_patterns,
                "string": str_obj,
            }
        )
        return False


async def generate_dict_hash(dict_obj: dict) -> str:
    return sha1(
        json.dumps(dict_obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


async def update_extended_request_expiration_date(
    tenant: str,
    user: str,
    extended_request: ExtendedRequestModel,
    expiration_date: datetime,
) -> ExtendedRequestModel:
    from common.lib.change_request import generate_policy_name, generate_policy_sid

    extended_request.expiration_date = expiration_date
    extended_request = normalize_expiration_date(extended_request)

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


def mfa_enabled_for_config(tra_config):
    return bool(tra_config.mfa and tra_config.mfa.enabled)


async def save_tra_config(tenant: str, tra_config: TraConfig):
    await models.ModelAdapter(TraConfig, "save_tra_config").load_config(
        TRA_CONFIG_BASE_KEY, tenant
    ).from_model(tra_config).store_item()


async def get_tra_config(
    resource_summary: ResourceSummary = None,
    tenant: str = None,
    user_groups: list[str] = None,
    tra_config: TraConfig = None,
) -> TraConfig:
    """Retrieve the proper TRA config based on provided account, role, and user groups with temp access to the role.
    Config priority:
        1: group
            1.a requires_approval=False
            1.b mfa_enabled=False
            1.c enabled=True
            1.d enabled=False
        2: role
        3: account
    """
    assert resource_summary or tenant
    if not tenant:
        tenant = resource_summary.tenant
    update_config = False

    if not tra_config:
        tra_config: TraConfig = (
            models.ModelAdapter(TraConfig)
            .load_config(TRA_CONFIG_BASE_KEY, tenant)
            .model
        )
        if not tra_config:
            update_config = True
            tra_config = TraConfig()  # Default config

    # Set defaults
    if not tra_config.mfa:
        update_config = True
        tra_config.mfa = MfaSupport()
        # if mfa hasn't been explicitly set the default by checking if tenant has mfa support
        tra_config.mfa.enabled = bool(
            config.get_tenant_specific_key("secrets.mfa", tenant, False)
        )

    if not tra_config.supported_groups_tag:
        update_config = True
        tra_config.supported_groups_tag = get_tra_supported_groups_tag(tenant)
        tra_config.active_users_tag = get_active_tra_users_tag(tenant)

    if update_config:
        await save_tra_config(tenant, tra_config)

    if not tra_config.approval_rules or not resource_summary:
        return tra_config

    role = resource_summary.name
    account = resource_summary.account
    config_attrs = [
        "requires_approval",
        "enabled",
        "mfa",
    ]

    for approval_rule in tra_config.approval_rules:
        rule_hit = False

        if ignore_accounts := approval_rule.accounts.ignore:
            if re_match_any_pattern(account, ignore_accounts):
                continue

        if include_accounts := approval_rule.accounts.include:
            rule_hit = re_match_any_pattern(account, include_accounts)

        if not rule_hit:
            rule_hit = re_match_any_pattern(role, approval_rule.roles)

        if user_groups and not rule_hit:
            for group in user_groups:
                if rule_hit := re_match_any_pattern(group, approval_rule.groups):
                    break

        if rule_hit:
            for config_attr in config_attrs:
                if (attr_val := getattr(approval_rule, config_attr, None)) is not None:
                    setattr(tra_config, config_attr, attr_val)

    return tra_config


def get_user_tra_groups_for_role(
    tenant: str, iam_role: IAMRole, user_groups: list[str]
):
    role_tags = get_resource_tag(
        iam_role.policy, get_tra_supported_groups_tag(tenant), default=[]
    )
    return [user_group for user_group in user_groups if user_group in role_tags]


async def get_tra_config_for_request(
    tenant: str, arn: str, user_groups: list[str]
) -> TraConfig:
    resource_summary = await ResourceSummary.set(tenant, arn)
    iam_role = await IAMRole.get(tenant, resource_summary.account, resource_summary.arn)
    tra_groups = get_user_tra_groups_for_role(tenant, iam_role, user_groups)
    return await get_tra_config(resource_summary, user_groups=tra_groups)


def get_active_tra_users_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        f"{TRA_CONFIG_BASE_KEY}.active_users_tag", tenant, TRA_USERS_TAG
    )


def get_tra_supported_groups_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        f"{TRA_CONFIG_BASE_KEY}.supported_groups_tag",
        tenant,
        TRA_SUPPORT_TAG,
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
