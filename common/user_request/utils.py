import time

from common.config import config
from common.lib.auth import can_admin_all


async def can_approve_reject_request(user, secondary_approvers, groups, host):
    # Allow admins to approve and reject all requests
    if can_admin_all(user, groups, host):
        return True

    if secondary_approvers:
        for g in secondary_approvers:
            if g in groups or g == user:
                return True
    return False


async def can_cancel_request(current_user, requesting_user, groups, host):
    # Allow the requesting user to cancel their own request
    if current_user == requesting_user:
        return True

    # Allow admins to cancel requests
    if can_admin_all(current_user, groups, host):
        return True

    # Allow restricted admins to cancel requests
    for g in config.get_host_specific_key("groups.can_admin_restricted", host):
        if g in groups:
            return True

    return False


async def can_move_back_to_pending(current_user, request, groups, host):
    # Don't allow returning requests to pending state if more than a day has passed since the last update
    if request.get("last_updated", 0) < int(time.time()) - 86400:
        return False
    # Allow admins to return requests back to pending state
    if can_admin_all(current_user, groups, host):
        return True
    return False


def get_pending_requests_url(host):
    return f"{config.get_host_specific_key('url', host)}/accessui/pending"


def get_request_review_url(request_id: str, host: str) -> str:
    return f"{config.get_host_specific_key('url', host)}/accessui/request/{request_id}"


def get_accessui_pending_requests_url(host):
    return f"{config.get_host_specific_key('accessui_url', host)}/requests"


def get_accessui_request_review_url(request_id, host):
    return f"{config.get_host_specific_key('accessui_url', host)}/requests/{request_id}"
