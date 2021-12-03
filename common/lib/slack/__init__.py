import sys

import tornado.escape
import ujson as json
from identity.lib.groups.models import GroupRequest
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest
from tornado.httputil import HTTPHeaders

from common.config import config
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_policy_request_uri_v2
from common.models import ExtendedRequestModel

log = config.get_logger()
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


async def send_slack_notification_new_request(
    extended_request: ExtendedRequestModel,
    admin_approved,
    approval_probe_approved,
    host,
):
    """
    Sends a notification using specified webhook URL about a new request created
    """
    if not config.get_host_specific_key(
        f"site_configs.{host}.slack.notifications_enabled", host, False
    ):
        return

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = extended_request.requester_email
    arn = extended_request.principal.principal_arn
    stats.count(function, tags={"user": requester, "arn": arn})

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": requester,
        "arn": arn,
        "host": host,
        "message": "Incoming request for slack notification",
        "request": extended_request.dict(),
        "admin_approved": admin_approved,
        "approval_probe_approved": approval_probe_approved,
    }
    log.debug(log_data)
    slack_webhook_url = config.get_host_specific_key(
        f"site_configs.{host}.slack.webhook_url", host
    )
    if not slack_webhook_url:
        log_data["message"] = "Missing webhook URL for slack notification"
        log.error(log_data)
        return
    payload = await get_payload(
        extended_request, requester, arn, admin_approved, approval_probe_approved, host
    )
    http_headers = HTTPHeaders({"Content-Type": "application/json"})
    http_req = HTTPRequest(
        url=slack_webhook_url,
        method="POST",
        headers=http_headers,
        body=json.dumps(payload),
    )
    http_client = AsyncHTTPClient(force_instance=True)
    try:
        await http_client.fetch(request=http_req)
        log_data["message"] = "Slack notification sent"
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending slack notification"
        log_data["error"] = str(e)
        log.error(log_data)


async def get_payload(
    extended_request: ExtendedRequestModel,
    requester: str,
    arn: str,
    admin_approved: bool,
    approval_probe_approved: bool,
    host: str,
):
    request_uri = await get_policy_request_uri_v2(extended_request, host)
    pre_text = "A new request has been created"
    if admin_approved:
        pre_text += " and auto-approved by admin"
    elif approval_probe_approved:
        pre_text += " and auto-approved by auto-approval probe"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{request_uri}|ConsoleMe Policy Change Request>*",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*User* \n {requester}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Resource* \n {arn}"},
            },
            {
                "type": "section",
                "fields": [
                    {"text": "*Justification*", "type": "mrkdwn"},
                    {"type": "plain_text", "text": "\n"},
                    {
                        "type": "plain_text",
                        "text": f"{tornado.escape.xhtml_escape(extended_request.justification)}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{pre_text}. Click *<{request_uri}|here>* to view it.",
                },
            },
        ]
    }
    return payload


async def send_slack_notification_new_group_request(
    host,
    request: GroupRequest,
):
    """
    Sends a notification using specified webhook URL about a new identity request
    """
    if not config.get_host_specific_key(
        f"site_configs.{host}.slack.notifications_enabled", host, False
    ):
        return

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = request.requester.username
    requested_users = ", ".join(user.username for user in request.users)
    requested_groups = ", ".join(group.name for group in request.groups)

    log_data: dict = {
        "function": function,
        "requester": requester,
        "requested_users": requested_users,
        "requested_groups": requested_groups,
        "host": host,
        "message": "Incoming request for slack notification",
        "request": json.loads(request.json()),
    }
    log.debug(log_data)
    slack_webhook_url = config.get_host_specific_key(
        f"site_configs.{host}.slack.webhook_url", host
    )
    if not slack_webhook_url:
        log_data["message"] = "Missing webhook URL for slack notification"
        log.error(log_data)
        return
    payload = await get_payload_for_group_request(
        request, requester, requested_users, requested_groups, host
    )
    http_headers = HTTPHeaders({"Content-Type": "application/json"})
    http_req = HTTPRequest(
        url=slack_webhook_url,
        method="POST",
        headers=http_headers,
        body=json.dumps(payload),
    )
    http_client = AsyncHTTPClient(force_instance=True)
    try:
        await http_client.fetch(request=http_req)
        log_data["message"] = "Slack notification sent"
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending slack notification"
        log_data["error"] = str(e)
        log.error(log_data)


async def get_payload_for_group_request(
    request, requester, requested_users, requested_groups, host
):
    host_url = config.get_host_specific_key(f"site_configs.{host}.url", host)
    if not host_url:
        raise Exception("No host URI")
    request_uri = f"{host_url}/{request.request_url}".replace("//", "/")

    pre_text = "A new request has been created"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{request_uri}|Group Request>*",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Requester* \n {requester}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Users* \n {requested_users}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Groups* \n {requested_groups}"},
            },
            {
                "type": "section",
                "fields": [
                    {"text": "*Justification*", "type": "mrkdwn"},
                    {"type": "plain_text", "text": "\n"},
                    {
                        "type": "plain_text",
                        "text": f"{tornado.escape.xhtml_escape(request.justification)}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{pre_text}. Click *<{request_uri}|here>* to view it.",
                },
            },
        ]
    }
    return payload


async def get_payload_for_policy_notification(
    message, session_name, arn, event_call, resource, source_ip, request_url
):

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Session Name* \n {session_name}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*ARN* \n {arn}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Event* \n {event_call}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Resource* \n {resource}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Source IP* \n {source_ip}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Request Permission",
                            "emoji": True,
                        },
                        "value": "request_url",
                        "url": f"{request_url}",
                    }
                ],
            },
        ]
    }
    return payload


async def send_slack_notification_new_notification(
    host, arn, event_call, resource, source_ip, session_name, encoded_request_url
):
    """
    Sends a notification using specified webhook URL about a new identity request
    """
    if not config.get_host_specific_key(
        f"site_configs.{host}.slack.notifications_enabled", host, False
    ):
        return

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    log_data: dict = {
        "function": function,
        "host": host,
        "arn": arn,
        "event_call": event_call,
        "resource": resource,
        "source_ip": source_ip,
        "session_name": session_name,
    }
    log.debug(log_data)
    slack_webhook_url = config.get_host_specific_key(
        f"site_configs.{host}.slack.webhook_url", host
    )
    if not slack_webhook_url:
        log_data["message"] = "Missing webhook URL for slack notification"
        log.error(log_data)
        return
    message = "We've generated a policy to resolve a detected permissions error"
    request_url = (
        config.get_host_specific_key(f"site_configs.{host}.url", host)
        + encoded_request_url
    )
    payload = await get_payload_for_policy_notification(
        message, session_name, arn, event_call, resource, source_ip, request_url
    )
    http_headers = HTTPHeaders({"Content-Type": "application/json"})
    http_req = HTTPRequest(
        url=slack_webhook_url,
        method="POST",
        headers=http_headers,
        body=json.dumps(payload),
    )
    http_client = AsyncHTTPClient(force_instance=True)
    try:
        await http_client.fetch(request=http_req)
        log_data["message"] = "Slack notification sent"
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending slack notification"
        log_data["error"] = str(e)
        log.error(log_data)
