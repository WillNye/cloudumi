import asyncio
import time
from typing import Any

from asgiref.sync import sync_to_async

from cloudumi_common.config import config
from cloudumi_common.exceptions.exceptions import NoMatchingRequest
from cloudumi_common.lib.auth import can_admin_all
from cloudumi_common.lib.cache import store_json_results_in_redis_and_s3
from cloudumi_common.lib.dynamo import UserDynamoHandler
from cloudumi_common.lib.plugins import get_plugin_by_name


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
    for g in config.get_host_specific_key(
        f"site_configs.{host}.groups.can_admin_restricted", host
    ):
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


async def get_request_by_id(user, request_id, host):
    """Get request matching id and add the group's secondary approvers"""
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    try:
        requests = await sync_to_async(dynamo_handler.resolve_request_ids)(
            [request_id], host
        )
        for req in requests:
            group = req.get("group")
            auth = get_plugin_by_name(
                config.get_host_specific_key(
                    f"site_configs.{host}.plugins.auth", host, "cmsaas_auth"
                )
            )()
            secondary_approvers = await auth.get_secondary_approvers(group, host)
            req["secondary_approvers"] = ",".join(secondary_approvers)
    except NoMatchingRequest:
        requests = []
    return next(iter(requests), None)


async def get_all_pending_requests_api(user, host):
    """Get all pending requests and add the group's secondary approvers"""
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    all_requests = await dynamo_handler.get_all_requests(host)
    auth = get_plugin_by_name(
        config.get_host_specific_key(
            f"site_configs.{host}.plugins.auth", host, "cmsaas_auth"
        )
    )()
    pending_requests = []

    # Get secondary approvers for groups asynchronously, otherwise this can be a bottleneck
    tasks = []
    for req in all_requests:
        if req.get("status") == "pending":
            group = req.get("group")
            task = asyncio.ensure_future(
                auth.get_secondary_approvers(group, return_dict=True)
            )
            tasks.append(task)
            pending_requests.append(req)
    secondary_approver_responses = asyncio.gather(*tasks)
    secondary_approver_mapping = {}
    for mapping in await secondary_approver_responses:
        for group, secondary_approvers in mapping.items():
            secondary_approver_mapping[group] = ",".join(secondary_approvers)

    for req in pending_requests:
        req["secondary_approvers"] = secondary_approver_mapping.get(
            req.get("group"), ""
        )
    return pending_requests


async def get_app_pending_requests_policies(user, host):
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    all_policy_requests = await dynamo_handler.get_all_policy_requests(
        host, status="pending"
    )
    if not all_policy_requests:
        all_policy_requests = []
    return all_policy_requests


async def get_all_policy_requests(user, host, status=None):
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    all_policy_requests = await dynamo_handler.get_all_policy_requests(
        host, status=status
    )
    if not all_policy_requests:
        all_policy_requests = []
    return all_policy_requests


async def cache_all_policy_requests(
    user="consoleme",
    redis_key=None,
    s3_bucket=None,
    s3_key=None,
    host=None,
):
    if not host:
        raise Exception("Unknown host")
    if not redis_key:
        redis_key = config.get_host_specific_key(
            f"site_configs.{host}.cache_policy_requests.redis_key",
            host,
            f"{host}_ALL_POLICY_REQUESTS",
        )
    if not s3_bucket and not s3_key:
        if config.region == config.get_host_specific_key(
            f"site_configs.{host}.celery.active_region", host, config.region
        ) or config.get_host_specific_key(f"site_configs.{host}.environment", host) in [
            "dev",
            "test",
        ]:
            s3_bucket = config.get_host_specific_key(
                f"site_configs.{host}.cache_policy_requests.s3.bucket", host
            )
            s3_key = config.get_host_specific_key(
                f"site_configs.{host}.cache_policy_requests.s3.file",
                host,
                "policy_requests/all_policy_requests_v1.json.gz",
            )
    requests = await get_all_policy_requests(user, host)
    requests_to_cache = []
    for request in requests:
        requests_to_cache.append(request)
    requests_to_cache = sorted(
        requests_to_cache, key=lambda i: i.get("request_time", 0), reverse=True
    )
    await store_json_results_in_redis_and_s3(
        requests_to_cache,
        redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        host=host,
    )
    return requests_to_cache


async def get_all_pending_requests(user, groups, host):
    """Get all pending requests sorted into three buckets:
    - all_pending_requests
    - my_pending_requests
    - pending_requests_waiting_my_approval

    Note: This will get pending requests for both POLICIES and GROUPS. If you are re-writing this feature, you may only
    want one or the other.
    """
    all_requests = await get_all_pending_requests_api(user, host)

    pending_requests = {
        "all_pending_requests": all_requests,
        "my_pending_requests": [],
        "pending_requests_waiting_my_approval": [],
    }

    for req in all_requests:
        req["secondary_approvers"] = req.get("secondary_approvers").split(",")
        if user == req.get("username", ""):
            pending_requests["my_pending_requests"].append(req)
        for sa in req["secondary_approvers"]:
            if sa in groups or sa == user:
                pending_requests["pending_requests_waiting_my_approval"].append(req)
                break

    all_policy_requests = await get_app_pending_requests_policies(user, host)
    pending_requests["all_pending_requests"].extend(all_policy_requests)

    for req in all_policy_requests:
        req["secondary_approvers"] = config.get_host_specific_key(
            f"site_configs.{host}.groups.can_admin_policies", host
        )

        for sa in req["secondary_approvers"]:
            if sa in groups or sa == user:
                pending_requests["pending_requests_waiting_my_approval"].append(req)
                break
        if user == req.get("username", ""):
            pending_requests["my_pending_requests"].append(req)

    return pending_requests


async def get_user_requests(user, groups, host):
    """Get requests relevant to a user.

    A user sees group requests they have made as well as requests where they are a
    secondary approver
    """
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    all_requests = await dynamo_handler.get_all_requests(host)
    query = {
        "domains": config.get_host_specific_key(
            f"site_configs.{host}.dynamo.get_user_requests.domains", host, []
        ),
        "filters": [
            {
                "field": "extendedattributes.attributeName",
                "values": ["secondary_approvers"],
                "operator": "EQUALS",
            },
            {
                "field": "extendedattributes.attributeValue",
                "values": groups + [user],
                "operator": "EQUALS",
            },
        ],
        "size": 500,
    }
    auth = get_plugin_by_name(
        config.get_host_specific_key(
            f"site_configs.{host}.plugins.auth", host, "cmsaas_auth"
        )
    )()
    approver_groups = await auth.query_cached_groups(query=query)
    approver_groups = [g["name"] for g in approver_groups]

    requests = []
    for req in all_requests:

        if user == req.get("username", ""):
            requests.append(req)
            continue

        group = req.get("group")
        if group is None:
            continue
        if group in approver_groups + [user]:
            requests.append(req)

    return requests


async def get_existing_pending_approved_request(
    user: str, group_info: Any, host: str
) -> None:
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    existing_requests = await sync_to_async(dynamo_handler.get_requests_by_user)(
        user, host
    )
    if existing_requests:
        for request in existing_requests:
            if group_info.get("name") == request.get("group") and request.get(
                "status"
            ) in ["pending", "approved"]:
                return request
    return None


async def get_existing_pending_request(user: str, group_info: Any, host: str) -> None:
    dynamo_handler = UserDynamoHandler(user=user, host=host)
    existing_requests = await sync_to_async(dynamo_handler.get_requests_by_user)(
        user, host
    )
    if existing_requests:
        for request in existing_requests:
            if group_info.get("name") == request.get("group") and request.get(
                "status"
            ) in ["pending"]:
                return request
    return None


def get_pending_requests_url(host):
    return f"{config.get(f'site_configs.{host}.url')}/accessui/pending"


def get_request_review_url(request_id: str, host: str) -> str:
    return f"{config.get(f'site_configs.{host}.url')}/accessui/request/{request_id}"


def get_accessui_pending_requests_url(host):
    return f"{config.get(f'site_configs.{host}.accessui_url')}/requests"


def get_accessui_request_review_url(request_id, host):
    return f"{config.get(f'site_configs.{host}.accessui_url')}/requests/{request_id}"
