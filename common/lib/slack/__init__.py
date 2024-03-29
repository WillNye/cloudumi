import sys

import requests
import tornado.escape
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest
from tornado.httputil import HTTPHeaders

import common.lib.noq_json as json
from common.config import config
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_policy_request_uri_v2
from common.models import ExtendedRequestModel
from identity.lib.groups.models import GroupRequest

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


def send_slack_notification_sync(log_data, payload, slack_webhook_url):
    if not slack_webhook_url:
        return

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(
            slack_webhook_url, headers=headers, data=json.dumps(payload)
        )
        if response.status_code == 200:
            log_data["message"] = "Slack notification sent"
            log.debug(log_data)
        else:
            log_data["message"] = "Error occurred sending Slack notification"
            log_data["error"] = f"Status code: {response.status_code}"
            log.error(log_data)
    except requests.exceptions.RequestException as e:
        log_data["message"] = "Error occurred sending Slack notification"
        log_data["error"] = str(e)
        log.error(log_data)


async def _send_slack_notification(tenant, log_data, payload):
    if not config.get_tenant_specific_key(
        "slack.notifications_enabled", tenant, False
    ) and not config.get_tenant_specific_key("slack.enabled", tenant, False):
        return

    slack_webhook_url = config.get_tenant_specific_key("slack.webhook_url", tenant)
    if not slack_webhook_url:
        log_data["message"] = "Missing webhook URL for slack notification"
        log.error(log_data)
        return

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


async def send_slack_notification_new_request(
    extended_request: ExtendedRequestModel,
    admin_approved,
    approval_rule_approved,
    tenant,
):
    """
    Sends a notification using specified webhook URL about a new request created
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = extended_request.requester_email
    arn = extended_request.principal.principal_arn
    stats.count(
        function,
        tags={
            "user": requester,
            "arn": arn,
            "tenant": tenant,
        },
    )

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": requester,
        "arn": arn,
        "tenant": tenant,
        "message": "Incoming request for slack notification",
        "request": extended_request.dict(),
        "admin_approved": admin_approved,
        "approval_rule_approved": approval_rule_approved,
    }
    log.debug(log_data)
    payload = await get_payload(
        extended_request,
        requester,
        arn,
        admin_approved,
        approval_rule_approved,
        tenant,
    )
    await _send_slack_notification(tenant, log_data, payload)


async def get_payload(
    extended_request: ExtendedRequestModel,
    requester: str,
    arn: str,
    admin_approved: bool,
    approval_rule_approved: bool,
    tenant: str,
):
    request_uri = await get_policy_request_uri_v2(extended_request, tenant)
    pre_text = "A new request has been created"
    if admin_approved:
        pre_text += " and auto-approved by admin"
    elif approval_rule_approved:
        pre_text += " and auto-approved by auto-approval rule"

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<{request_uri}|Noq Policy Change Request>*",
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
    tenant,
    request: GroupRequest,
):
    """
    Sends a notification using specified webhook URL about a new identity request
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    requester = request.requester.username
    requested_users = ", ".join(user.username for user in request.users)
    requested_groups = ", ".join(group.name for group in request.groups)

    log_data: dict = {
        "function": function,
        "requester": requester,
        "requested_users": requested_users,
        "requested_groups": requested_groups,
        "tenant": tenant,
        "message": "Incoming request for slack notification",
        "request": json.loads(request.json()),
    }
    log.debug(log_data)
    payload = await get_payload_for_group_request(
        request, requester, requested_users, requested_groups, tenant
    )
    await _send_slack_notification(tenant, log_data, payload)


async def get_payload_for_group_request(
    request, requester, requested_users, requested_groups, tenant
):
    tenant_url = config.get_tenant_specific_key("url", tenant)
    if not tenant_url:
        raise Exception("No tenant URI")
    request_uri = f"{tenant_url}/{request.request_url}".replace("//", "/")

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
    tenant, arn, event_call, resource, source_ip, session_name, encoded_request_url
):
    """
    Sends a notification using specified webhook URL about a new identity request
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    log_data: dict = {
        "function": function,
        "tenant": tenant,
        "arn": arn,
        "event_call": event_call,
        "resource": resource,
        "source_ip": source_ip,
        "session_name": session_name,
    }
    log.debug(log_data)
    message = "We've generated a policy to resolve a detected permissions error"
    request_url = config.get_tenant_specific_key("url", tenant) + encoded_request_url
    payload = await get_payload_for_policy_notification(
        message, session_name, arn, event_call, resource, source_ip, request_url
    )
    await _send_slack_notification(tenant, log_data, payload)


# TODO|steven: Unused identities slack notification is still WIP
def get_payload_for_unused_identities(message, account_id):

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
                "text": {"type": "mrkdwn", "text": f"*Account ID* \n {account_id}"},
            },
        ]
    }
    return payload


# TODO|steven: Unused identities slack notification is still WIP
async def send_slack_notification_unused_identities(tenant, account_id):
    """
    Sends a notification using specified webhook URL about a new identity request
    """
    if not config.get_tenant_specific_key("slack.notifications_enabled", tenant, False):
        return

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    log_data: dict = {
        "function": function,
        "tenant": tenant,
        "account_id": account_id,
    }
    log.debug(log_data)
    message = "WIP - unused identities"
    payload = get_payload_for_unused_identities(message, account_id)
    await _send_slack_notification(tenant, log_data, payload)
