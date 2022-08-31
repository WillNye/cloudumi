import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import sentry_sdk

from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.auth import get_extended_request_allowed_approvers
from common.lib.aws.session import get_session_for_tenant
from common.lib.generic import generate_html, get_principal_friendly_name
from common.lib.groups import get_group_url
from common.lib.plugins import get_plugin_by_name
from common.models import ExtendedRequestModel, RequestStatus

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


async def send_email_via_ses(
    to_addresses: list[str],
    subject: str,
    body: str,
    tenant: str,
    sending_app: str = "noq",
    charset: str = "UTF-8",
) -> None:

    region: str = config.get_tenant_specific_key("ses.region", tenant, config.region)
    sender = config.get(f"_global_.ses.{sending_app}.sender")
    ses_arn = config.get_tenant_specific_key("ses.arn", tenant)
    log_data = {
        "to_user": to_addresses,
        "region": region,
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "sender": sender,
        "subject": subject,
        "tenant": tenant,
    }

    if not ses_arn:
        log.error(
            {
                **log_data,
                "error": "Configuration value for `ses.arn` is not defined. Unable to send e-mail.",
            }
        )
        return

    if not sender:
        log.error(
            {
                **log_data,
                "error": f"Configuration value for `_global_.ses.{sending_app}.sender` is not defined. Unable to send e-mail.",
            }
        )
        return

    session = get_session_for_tenant(tenant)
    client = session.client(
        "ses",
        region_name=region,
        **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
    )
    try:
        response = await aio_wrapper(
            client.send_email,
            Destination={"ToAddresses": to_addresses},  # This should be a list
            Message={
                "Body": {
                    "Html": {"Charset": charset, "Data": body},
                    "Text": {"Charset": charset, "Data": body},
                },
                "Subject": {"Charset": charset, "Data": subject},
            },
            Source=sender,
            SourceArn=ses_arn,
        )
    # Display an error if something goes wrong.
    except Exception:
        stats.count("lib.ses.error")
        log_data["message"] = "Exception sending email"
        log.error(log_data, exc_info=True)
    else:
        stats.count("lib.ses.success")
        log_data["message"] = "Email sent successfully"
        log_data["response"] = response["MessageId"]
        log.debug(log_data)


async def send_email_via_sendgrid(
    to_addresses: list[str],
    subject: str,
    body: str,
    charset: str = "UTF-8",
):
    server = smtplib.SMTP_SSL("smtp.sendgrid.net", 465)
    key_space = "_global_.secrets.sendgrid"
    sender = config.get(f"{key_space}.from_address")
    log_data = {
        "to_user": to_addresses,
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "sender": sender,
        "subject": subject,
    }

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ";".join(to_addresses)
    msg.attach(MIMEText(body, "html", _charset=charset))

    try:
        server.ehlo()
        await aio_wrapper(
            server.login,
            config.get(f"{key_space}.username"),
            config.get(f"{key_space}.password"),
        )
        await aio_wrapper(server.send_message, msg)
        server.close()
    except Exception:
        stats.count("lib.ses.error")
        log_data["message"] = "Exception sending email"
        log.error(log_data, exc_info=True)
    else:
        stats.count("lib.ses.success")
        log_data["message"] = "Email sent successfully"
        log.debug(log_data)


async def send_email(
    to_addresses: List[str],
    subject: str,
    body: str,
    tenant: str,
    sending_app: str = "noq",
    charset: str = "UTF-8",
) -> None:
    # Handle non-list recipients
    if not isinstance(to_addresses, list):
        to_addresses = [to_addresses]

    if config.is_development and config.get("_global_.ses.override_receivers_for_dev"):
        to_addresses = config.get("_global_.ses.override_receivers_for_dev")
        log.debug(
            {"message": "Overriding to_address", "new_to_addresses": to_addresses}
        )
    elif config.is_development:
        log_data = {
            "to_user": to_addresses,
            "function": f"{__name__}.{sys._getframe().f_code.co_name}",
            "subject": subject,
            "tenant": tenant,
            "message": "E-Mail not sent.",
            "reason": "The development flag on global config was set with no override receivers",
            "body": body,
        }
        log.warning(log_data)
        return

    try:
        # Once we know under what conditions to use which provider we can update to support sending via ses
        await send_email_via_sendgrid(to_addresses, subject, body, charset)
    except Exception as err:
        log.exception(repr(err))
        sentry_sdk.capture_exception()


async def send_access_email_to_user(
    user: str,
    group: str,
    updated_by: str,
    status: str,
    request_url: str,
    group_url: str,
    tenant: str,
    reviewer_comments: None = None,
    sending_app: str = "noq",
) -> None:
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: Request for group {group} has been {status}"
    to_addresses = [user, updated_by]
    group_link = f"<a href={group_url}>{group}</a>"
    message = f"Your request for group {group_link} has been {status} by {updated_by}."
    if status == "approved":
        message += " Please allow up to 30 minutes for your group to propagate. "

    reviewer_comments_section = ""
    if reviewer_comments:
        reviewer_comments_section = f"Reviewer Comments: {reviewer_comments}"
    body = f"""<html>
    <head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>Request Status</title>
    </head>
    <body>
    {message} <br>
    {reviewer_comments_section} <br>
    See your request here: {request_url}.<br>
    <br>
    {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    </body>
    </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_request_created_to_user(
    user, group, updated_by, status, request_url, tenant, sending_app="noq"
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: Request for group {group} has been created"
    to_addresses = [user, updated_by]
    message = f"Your request for group {group} has been created."
    if status == "approved":
        message += " Please allow up to 30 minutes for your group to propagate. "
    body = f"""<html>
    <head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>Request Status</title>
    </head>
    <body>
    {message} <br>
    <br>
    See your request here: {request_url}.<br>
    <br>
    {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    </body>
    </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_request_to_secondary_approvers(
    secondary_approvers,
    group,
    request_url,
    pending_requests_url,
    tenant: str,
    sending_app="noq",
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: A request for group {group} requires your approval"
    to_addresses = secondary_approvers
    message = f"A request for group {group} requires your approval."
    body = f"""<html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        <title>Request Status</title>
        </head>
        <body>
        {message} <br>
        <br>
        See the request here: {request_url}.<br>
        <br>
        You can find all pending requests waiting your approval here: {pending_requests_url}. <br>
        <br>
        {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        </body>
        </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_group_modification_notification(
    groups, to_address, tenant, sending_app="noq"
):
    """
    Send an email containing group changes to a notification address

    Example of `groups` dict:
    {
        "awesome_group_1@netflix.com": [
            {"name": "tswift@netflix.com", "type": "USER"},
            {"name": "agrande@netflix.com", "type": "USER"},
        ],
        "awesome_group_2@netflix.com": [
            {"name": "lizzo@netflix.com", "type": "USER"},
            {"name": "beilish@netflix.com", "type": "USER"},
        ],
    }

    :param groups: map of groups and added members
    :type groups: dict
    :param to_address: recipient of notification email
    :type to_address: str
    :param sending_app: name of application
    :type sending_app: str
    """
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: Groups modified"
    message = f"""Groups modified in {app_name}.<br>
    You or a group you belong to are configured to receive a notification when new members are added to this group.<br>
    Admins may click the group link below to view and modify this configuration."""
    added_members_snippet = ""
    for group, added_members in groups.items():
        group_url = get_group_url(group, tenant)
        group_link = f"<a href={group_url}>{group}</a>"
        if added_members:
            added_members_snippet += f"""<b>Users added to {group_link}</a></b>: <br>
            {generate_html(added_members)}<br>
            """
    body = f"""<html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        </head>
        <body>
         {message}<br>
         <br>
         {added_members_snippet}<br>
        <br>
        <br>
        {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        </body>
        </html>"""
    await send_email(to_address, subject, body, tenant, sending_app=sending_app)


async def send_new_aws_groups_notification(
    to_addresses, new_aws_groups, tenant, sending_app="noq"
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: New AWS groups detected"
    message = """New AWS login groups were created.<br>
    Noq is configured to send notifications when new AWS-related google groups are detected.
    This is to detect any accidentally or maliciously created google groups.<br>"""
    added_groups_snippet = ""
    if new_aws_groups:
        added_groups_snippet = f"""<b>New groups</b>: <br>
        {generate_html({"New Groups": new_aws_groups})}<br>
        """
    body = f"""<html>
        <head>
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        </head>
        <body>
         {message}<br>
         <br>
         {added_groups_snippet}<br>
        <br>
        <br>
        {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
        <meta http-equiv="content-type" content="text/html; charset=UTF-8">
        </body>
        </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_policy_request_status_update(
    request, policy_change_uri, tenant: str, sending_app="noq"
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    subject = f"{app_name}: Policy change request for {request['arn']} has been {request['status']}"
    if request["status"] == "pending":
        subject = (
            f"{app_name}: Policy change request for {request['arn']} has been created"
        )
    to_addresses = [request.get("username")]
    message = (
        f"A policy change request for {request['arn']} has been {request['status']}"
    )
    if request["status"] == "pending":
        message = f"A policy change request for {request['arn']} has been created."
    if {request["status"]} == "approved":
        message += " and committed"
        subject += " and committed"
    body = f"""<html>
            <head>
            <meta http-equiv="content-type" content="text/html; charset=UTF-8">
            <title>Policy Change Request Status Change</title>
            </head>
            <body>
            {message} <br>
            <br>
            See the request here: {policy_change_uri}.<br>
            <br>
            <br>
            {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
            <meta http-equiv="content-type" content="text/html; charset=UTF-8">
            </body>
            </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_policy_request_status_update_v2(
    extended_request: ExtendedRequestModel,
    policy_change_uri,
    tenant,
    sending_app="noq",
    auto_approved: bool = False,
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    user_email = extended_request.requester_email
    request_approvers = set()
    request_approvers.add(user_email)
    principal = await get_principal_friendly_name(extended_request.principal)
    is_tear_request = any(
        c.change_type == "tear_can_assume_role"
        for c in extended_request.changes.changes
    )
    change_type = "Policy Change" if not is_tear_request else "Temporary Access"

    if extended_request.request_status == RequestStatus.pending:
        subject = f"{app_name}: {change_type} request for {principal} has been created"
        message = f"A {change_type} request for {principal} has been created."
        # This is a new request, also send email to application admins
        resource_admins = await get_extended_request_allowed_approvers(
            extended_request, tenant
        )
        request_approvers.update(resource_admins)
    elif extended_request.request_status == RequestStatus.approved and is_tear_request:
        subject = f"{app_name}: {user_email} has been granted temporary access to {principal}."
        message = subject
        if auto_approved:
            message += " NOQ was able auto-approve this request based on your NOQ configuration."

        resource_admins = await get_extended_request_allowed_approvers(
            extended_request, tenant
        )
        request_approvers.update(resource_admins)
    else:
        subject = (
            f"{app_name}: {change_type} request for {principal} has been "
            f"updated to {extended_request.request_status.value}"
        )
        message = (
            f"A {change_type} request for {principal} "
            f"has been updated to {extended_request.request_status.value}"
        )

        if extended_request.request_status == RequestStatus.approved:
            message += " and committed"
            subject += " and committed"

    body = f"""<html>
            <head>
            <meta http-equiv="content-type" content="text/html; charset=UTF-8">
            <title>{change_type} Request Status Change</title>
            </head>
            <body>
            {message} <br>
            <br>
            See the request here: {policy_change_uri}.<br>
            <br>
            <br>
            {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
            <meta http-equiv="content-type" content="text/html; charset=UTF-8">
            </body>
            </html>"""
    to_addresses = list(request_approvers)
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)


async def send_new_comment_notification(
    extended_request: ExtendedRequestModel,
    to_addresses,
    user,
    policy_change_uri,
    tenant,
    sending_app="noq",
):
    app_name = config.get("_global_.ses.{sending_app}.name", sending_app)
    principal = await get_principal_friendly_name(extended_request.principal)
    subject = f"{app_name}: A new comment has been added to Policy Change request for {principal}"
    message = f"A new comment has been added to the policy change request for {principal} by {user}"
    body = f"""<html>
                <head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8">
                <title>Policy Change Request Comment Notification</title>
                </head>
                <body>
                {message} <br>
                <br>
                See the request here: {policy_change_uri}.<br>
                <br>
                <br>
                {config.get_tenant_specific_key('ses.support_reference', tenant, '')}
                <meta http-equiv="content-type" content="text/html; charset=UTF-8">
                </body>
                </html>"""
    await send_email(to_addresses, subject, body, tenant, sending_app=sending_app)
