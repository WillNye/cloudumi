import asyncio
import json
import time
from hashlib import sha1

from common.config import config
from common.lib.auth import can_admin_all
from common.models import ExtendedRequestModel


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
        if change.change_type in ["inline_policy"]:
            change.policy_name = await generate_policy_name(
                None, user, tenant, expiration_date
            )

        if change.change_type in ["resource_policy", "sts_resource_policy"]:
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


async def can_approve_reject_request(user, secondary_approvers, groups, tenant):
    # Allow admins to approve and reject all requests
    if can_admin_all(user, groups, tenant):
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
    if can_admin_all(current_user, groups, tenant):
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
    if can_admin_all(current_user, groups, tenant):
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
