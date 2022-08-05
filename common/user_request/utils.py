import asyncio
import json
import time
from hashlib import sha1

from common.aws.utils import ResourceSummary
from common.config import config
from common.lib.assume_role import boto3_cached_conn
from common.lib.auth import is_tenant_admin
from common.models import (
    CloudCredentials,
    Command,
    ExtendedRequestModel,
    PolicyRequestModificationRequestModel,
)

log = config.get_logger(__name__)


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
