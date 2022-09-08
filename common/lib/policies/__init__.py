import base64
import re
import sys
import time
import urllib
from collections import defaultdict
from typing import Dict, List, Optional

from deepdiff import DeepDiff
from policy_sentry.util.actions import get_service_from_action
from policy_sentry.util.arns import parse_arn

import common.lib.noq_json as json
from common.aws.utils import ResourceSummary
from common.config import config
from common.exceptions.exceptions import (
    InvalidRequestParameter,
    MissingConfigurationValue,
)
from common.lib.auth import can_admin_policies, get_extended_request_account_ids
from common.lib.notifications import (
    send_new_comment_notification,
    send_policy_request_status_update_v2,
)
from common.lib.plugins import get_plugin_by_name
from common.lib.role_updater.handler import update_role
from common.models import ExtendedRequestModel, RequestStatus

log = config.get_logger()
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()


async def invalid_characters_in_policy(policy_value):
    if not policy_value:
        return False
    if "<" in policy_value or ">" in policy_value:
        return True
    return False


def escape_json(code):
    escaped = re.sub(
        r"(?<=</)s(?=cript)", lambda m: f"\\u{ord(m.group(0)):04x}", code, flags=re.I
    )
    return escaped


async def parse_policy_change_request(
    user: str, arn: str, role: str, data_list: list, tenant: str
) -> dict:
    result: dict = {"status": "success"}

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(
        function,
        tags={
            "user": user,
            "arn": arn,
            "role": role,
            "tenant": tenant,
        },
    )

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "user": user,
        "role": role,
        "data_list": data_list,
        "arn": arn,
        "message": "Incoming request",
    }

    log.debug(log_data)
    events: list = []

    for data in data_list:
        requester: str = user

        # Make sure the requester is only ever 64 chars with domain
        if len(requester) > 64:
            split_items: list = requester.split("@")
            requester: str = (
                split_items[0][: (64 - (len(split_items[-1]) + 1))]
                + "@"
                + split_items[-1]
            )

        event: dict = {
            "arn": arn,
            "inline_policies": [],
            "managed_policies": [],
            "requester": requester,
        }
        if data.get("value") and await invalid_characters_in_policy(data["value"]):
            result["status"] = "error"
            result["error"] = "Invalid characters were detected in the policy."
            log_data["message"] = result["error"]
            log.error(log_data)
            return result
        if data["type"] == "InlinePolicy":
            name = data["name"]
            value = data.get("value")
            if value:
                value = json.loads(value)
            log_data["message"] = "Update inline policy"
            log_data["policy_name"] = name
            log_data["policy_value"] = value
            log.debug(log_data)

            # Check if policy being updated is the same as existing policy.
            # Check if a new policy is being created, ensure that we don't overwrite another policy with same name
            for existing_policy in role["policy"]["RolePolicyList"]:
                if data.get("is_new") and existing_policy.get("PolicyName") == name:
                    result["status"] = "error"
                    result[
                        "error"
                    ] = "You cannot make or request a new policy that has the same name as an existing policy."
                    log_data["message"] = result["error"]
                    log.error(log_data)
                    return result
                if existing_policy.get("PolicyName") == name:
                    if existing_policy.get("PolicyDocument") == value:
                        result["status"] = "error"
                        result[
                            "error"
                        ] = "No changes were found between the updated and existing policy."
                        log_data["message"] = result["error"]
                        log.error(log_data)
                        return result

            action = data.get("action", "attach")

            entry = {"action": action, "policy_name": name}
            if value:
                entry["policy_document"] = value

            event["inline_policies"].append(entry)
            events.append(event)
        if data["type"] == "ManagedPolicy":
            policy_arn = data["arn"]
            action = data["action"]
            policy_name = data["name"]
            log_data["message"] = "Update managed policy"
            log_data["action"] = action
            log_data["policy_arn"] = policy_arn
            log.debug(log_data)

            entry: dict = {"action": action, "arn": policy_arn}
            if action == "detach":
                seen = False
                for policy in role["policy"]["AttachedManagedPolicies"]:
                    if policy["PolicyName"] == policy_name:
                        seen = True
                        break
                if not seen:
                    result["status"] = "error"
                    result["error"] = (
                        f"There is no policy attached to role {arn} "
                        f"with arn {policy_arn} that can be removed."
                    )
                    log_data["message"] = result["error"]
                    log.error(log_data)
                    return result
                event["managed_policies"].append(entry)
                events.append(event)
            elif action == "attach":
                for policy in role["policy"]["AttachedManagedPolicies"]:
                    if policy["PolicyName"] == policy_name:
                        result["status"] = "error"
                        result["error"] = (
                            f"There is already a policy attached to role {arn} "
                            f"with arn {policy_arn}."
                        )
                        log_data["message"] = result["error"]
                        log.error(log_data)
                        return result
                event["managed_policies"].append(entry)
                events.append(event)

        elif data["type"] == "AssumeRolePolicyDocument":
            action = "update"
            value = json.loads(data["value"])
            log_data["message"] = "Update AssumeRolePolicyDocument"
            log_data["policy_value"] = data["value"]
            log.debug(log_data)

            # Check if policy being updated is the same as existing policy
            if role["policy"].get("AssumeRolePolicyDocument") == value:
                result["status"] = "error"
                result[
                    "error"
                ] = "No changes were found between the updated and existing assume role policy document."
                log_data["message"] = result["error"]
                log.error(log_data)
                return result

            # Todo(ccastrapel): Validate AWS syntax

            event["assume_role_policy_document"] = {
                "action": action,
                "assume_role_policy_document": value,
            }
            events.append(event)

        elif data["type"] == "delete_tag":
            action = "remove"
            key = data["name"]
            event["tags"] = [{"action": action, "key": key}]
            events.append(event)

        elif data["type"] == "update_tag":
            action = "add"
            key = data["name"]
            value = data["value"]
            event["tags"] = [{"action": action, "key": key, "value": value}]
            events.append(event)
    result["events"] = events
    return result


async def can_move_back_to_pending(request, current_user, groups, tenant):
    if request.get("status") in ["cancelled", "rejected"]:
        # Don't allow returning requests to pending state if more than a day has passed since the last update
        if request.get("last_updated", 0) < int(time.time()) - 86400:
            return False
        # Allow admins to return requests back to pending state
        if await can_admin_policies(current_user, groups, tenant):
            return True
    return False


async def can_move_back_to_pending_v2(
    extended_request: ExtendedRequestModel, last_updated, current_user, groups, tenant
):
    if extended_request.request_status in [
        RequestStatus.cancelled,
        RequestStatus.rejected,
    ]:
        # Don't allow returning requests to pending state if more than a day has passed since the last update
        if last_updated < int(time.time()) - 86400:
            return False
        # Allow admins to return requests back to pending state
        account_ids = await get_extended_request_account_ids(extended_request, tenant)
        if await can_admin_policies(current_user, groups, tenant, account_ids):
            return True
    return False


async def can_update_requests(request, user, groups, tenant):
    # Users can update their own requests
    can_update = user in request["username"]

    # Allow admins to return requests back to pending state
    if not can_update:
        if await can_admin_policies(user, groups, tenant):
            return True

    return can_update


async def can_update_cancel_requests_v2(
    extended_request: ExtendedRequestModel, user, groups, tenant, account_ids=None
):
    # Users can update their own requests
    can_update = user == extended_request.requester_email

    # Allow admins to update / cancel requests
    if not can_update:
        if not account_ids:
            account_ids = await get_extended_request_account_ids(
                extended_request, tenant
            )
        if await can_admin_policies(user, groups, tenant, account_ids):
            return True

    return can_update


async def update_role_policy(events, tenant: str, user: str):
    result = {"status": "success"}

    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    stats.count(function)

    log_data = {"function": function, "message": "Updating role policy"}

    response = await update_role(events, tenant, user)
    log_data["message"] = "Received Response"
    log_data["response"] = response
    log.debug(log_data)

    if not response.get("success"):
        log_data["message"] = "Error"
        log_data["error"] = response.get("message")
        log.error(log_data)
        result["status"] = "error"
        result["error"] = log_data["error"]
        return result

    return result


async def get_policy_request_uri_v2(
    extended_request: ExtendedRequestModel, tenant: str
):
    if extended_request.request_url:
        return extended_request.request_url
    return f"{config.get_tenant_specific_key('url', tenant)}/policies/request/{extended_request.id}"


async def validate_policy_name(policy_name):
    p = re.compile("^[a-zA-Z0-9+=,.@\\-_]+$")
    match = p.match(policy_name)
    if not match:
        raise InvalidRequestParameter(
            "The specified value for policyName is invalid. "
            "It must contain only alphanumeric characters and/or the following: +=,.@_-"
        )


async def get_resources_from_events(
    policy_changes: List[Dict], tenant: str
) -> Dict[str, dict]:
    """Returns a dict of resources affected by a list of policy changes along with
    the actions and other data points that are relevant to them.

    Returned dict format:
    {
        "resource_name": {
            "actions": ["service1:action1", "service2:action2"],
            "arns": ["arn:aws:service1:::resource_name", "arn:aws:service1:::resource_name/*"],
            "account": "1234567890",
            "type": "service1",
            "region": "",
        }
    }
    """

    def default_resource():
        return {"actions": [], "arns": [], "account": "", "type": "", "region": ""}

    resource_actions: Dict[str, Dict] = defaultdict(default_resource)
    for event in policy_changes:
        for policy_type in ["inline_policies", "managed_policies"]:
            for policy in event.get(policy_type, []):
                policy_document = policy["policy_document"]
                for statement in policy_document.get("Statement", []):
                    resources = statement.get("Resource", [])
                    resources = (
                        resources if isinstance(resources, list) else [resources]
                    )
                    for resource in resources:
                        if resource == "*":
                            continue
                        try:
                            resource_summary = await ResourceSummary.set(
                                tenant, resource, region_required=True
                            )
                        except ValueError:
                            continue

                        # Default to parent name to use bucket name for S3 objects
                        namespace = (
                            resource_summary.parent_name or resource_summary.name
                        )
                        if namespace == "*":
                            continue
                        if not resource_actions[namespace]["account"]:
                            resource_actions[namespace][
                                "account"
                            ] = resource_summary.account
                        if not resource_actions[namespace]["type"]:
                            resource_actions[namespace][
                                "type"
                            ] = resource_summary.service
                        if not resource_actions[namespace]["region"]:
                            resource_actions[namespace][
                                "region"
                            ] = resource_summary.region
                        resource_actions[namespace]["arns"].append(resource)
                        actions = get_actions_for_resource(resource, statement)
                        resource_actions[namespace]["actions"].extend(
                            x
                            for x in actions
                            if x not in resource_actions[namespace]["actions"]
                        )
    return dict(resource_actions)


def get_actions_for_resource(resource_arn: str, statement: Dict) -> List[str]:
    """For the given resource and policy statement, return the actions that are
    for that resource's service.
    """
    results: List[str] = []
    # Get service from resource
    resource_service = parse_arn(resource_arn)["service"]
    # Get relevant actions from policy doc
    actions = statement.get("Action", [])
    actions = actions if isinstance(actions, list) else [actions]
    for action in actions:
        if action == "*":
            results.append(action)
        else:
            if get_service_from_action(action) == resource_service:
                if action not in results:
                    results.append(action)

    return results


async def get_formatted_policy_changes(
    account_id, arn, request, tenant, force_refresh=False
):
    from common.aws.iam.role.models import IAMRole

    existing_role: IAMRole = await IAMRole.get(
        account_id, arn, tenant, force_refresh=force_refresh
    )
    policy_changes: list = json.loads(request.get("policy_changes"))
    formatted_policy_changes = []

    # Parse request json and figure out how to present to the page
    for policy_change in policy_changes:
        if not policy_change.get("inline_policies"):
            policy_change["inline_policies"] = []

        if len(policy_change.get("inline_policies")) > 1:
            raise InvalidRequestParameter(
                "Only one inline policy change at a time is currently supported."
            )

        for inline_policy in policy_change.get("inline_policies"):
            if policy_change.get("arn") != arn:
                raise InvalidRequestParameter(
                    "Only one role can be changed in a request"
                )
            policy_name = inline_policy.get("policy_name")
            await validate_policy_name(policy_name)
            policy_document = inline_policy.get("policy_document")
            old_policy = {}
            new_policy: bool = False
            existing_policy_document = {}
            if request.get("status") == "approved":
                old_policy = request.get("old_policy", {})
                if old_policy:
                    existing_policy_document = json.loads(old_policy)[0]
            if not old_policy:
                existing_inline_policies = existing_role.policy.get(
                    "RolePolicyList", []
                )
                existing_policy_document = {}
                for existing_policy in existing_inline_policies:
                    if existing_policy["PolicyName"] == policy_name:
                        existing_policy_document = existing_policy["PolicyDocument"]

            # Generate dictionary with old / new policy documents
            diff = DeepDiff(existing_policy_document, policy_document)

            if not existing_policy_document:
                new_policy = True

            formatted_policy_changes.append(
                {
                    "name": policy_name,
                    "old": existing_policy_document,
                    "new": policy_document,
                    "diff": diff,
                    "new_policy": new_policy,
                }
            )

        assume_role_policy_document = policy_change.get("assume_role_policy_document")
        if assume_role_policy_document:
            if policy_change.get("arn") != arn:
                raise InvalidRequestParameter(
                    "Only one role can be changed in a request"
                )
            existing_ar_policy = existing_role.policy["AssumeRolePolicyDocument"]
            old_policy = request.get("old_policy", {})
            if old_policy:
                existing_ar_policy = json.loads(old_policy)[0]

            diff = DeepDiff(
                existing_ar_policy,
                assume_role_policy_document.get("assume_role_policy_document"),
            )

            formatted_policy_changes.append(
                {
                    "name": "AssumeRolePolicyDocument",
                    "old": existing_ar_policy,
                    "new": assume_role_policy_document.get(
                        "assume_role_policy_document"
                    ),
                    "new_policy": False,
                    "diff": diff,
                }
            )

        resource_policy_documents = request.get("resource_policies")
        if resource_policy_documents:
            for resource in resource_policy_documents:
                existing_policy_document = None
                # TODO: make this actually fetch the resource policy
                # existing_policy_document = aws.fetch_resource_policy()
                new_policy_document = resource["policy_document"]
                diff = DeepDiff(existing_policy_document, new_policy_document)

                formatted_policy_changes.append(
                    {
                        "name": "ResourcePolicy",
                        "old": existing_policy_document,
                        "new": new_policy_document,
                        "new_policy": not existing_policy_document,
                        "diff": diff,
                    }
                )
    return {"changes": formatted_policy_changes, "role": existing_role.dict()}


async def should_auto_approve_policy_v2(
    extended_request: ExtendedRequestModel, user, user_groups, tenant
):
    """
    This uses your fancy internal logic to determine if a request should be auto-approved or not. The default plugin
    set included in Noq will return False.
    """
    aws = get_plugin_by_name(
        config.get_tenant_specific_key("plugins.aws", tenant, "cmsaas_aws")
    )()
    return await aws.should_auto_approve_policy_v2(
        extended_request, user, user_groups, tenant
    )


async def send_communications_policy_change_request_v2(
    extended_request: ExtendedRequestModel,
    tenant: str,
    auto_approved: bool = False,
):
    """
        Send an email for a status change for a policy request

    :param extended_request: ExtendedRequestModel
    :return:
    """
    request_uri = await get_policy_request_uri_v2(extended_request, tenant)
    await send_policy_request_status_update_v2(
        extended_request, request_uri, tenant, auto_approved=auto_approved
    )


async def send_communications_new_comment(
    extended_request: ExtendedRequestModel, user: str, tenant: str, to_addresses=None
):
    """
            Send an email for a new comment.
            Note: until ABAC work is completed, if to_addresses is empty, we will send an email to
                fallback reviewers

    :param extended_request: ExtendedRequestModel
    :param user: user making the comment
    :param to_addresses: List of addresses to send the email to
    :return:
    """
    if not to_addresses:
        to_addresses = config.get_tenant_specific_key(
            "groups.fallback_policy_request_reviewers", tenant, []
        )

    request_uri = await get_policy_request_uri_v2(extended_request, tenant)
    await send_new_comment_notification(
        extended_request, to_addresses, user, request_uri, tenant
    )


async def get_aws_config_history_url_for_resource(
    account_id,
    resource_id,
    resource_name,
    technology,
    tenant: str,
    region: Optional[str] = None,
):
    if not region:
        region = (config.get_tenant_specific_key("aws.region", tenant, config.region),)
    if config.get_tenant_specific_key(
        "get_aws_config_history_url_for_resource.generate_conglomo_url",
        tenant,
    ):
        return await get_conglomo_url_for_resource(
            account_id, resource_id, technology, tenant, region
        )

    encoded_redirect = urllib.parse.quote_plus(
        f"https://{region}.console.aws.amazon.com/config/home?#/resources/timeline?"
        f"resourceId={resource_id}&resourceName={resource_name}&resourceType={technology}"
    )

    url = f"/role/{account_id}?redirect={encoded_redirect}"
    return url


async def get_conglomo_url_for_resource(
    account_id, resource_id, technology, tenant, region="global"
):
    conglomo_url = config.get_tenant_specific_key(
        "get_aws_config_history_url_for_resource.conglomo_url",
        tenant,
    )
    if not conglomo_url:
        raise MissingConfigurationValue(
            "Unable to find conglomo URL in configuration: `get_aws_config_history_url_for_resource.conglomo_url`"
        )
    encoded_resource_id = base64.urlsafe_b64encode(resource_id.encode("utf-8")).decode(
        "utf-8"
    )
    return f"{conglomo_url}/resource/{account_id}/{region}/{technology}/{encoded_resource_id}"
