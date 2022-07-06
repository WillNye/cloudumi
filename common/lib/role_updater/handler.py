import sys
import traceback

from botocore.exceptions import ClientError

import common.lib.noq_json as json
from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.plugins import get_plugin_by_name
from common.lib.role_updater.schemas import RoleUpdaterRequest
from common.models import SpokeAccount

log = config.get_logger()
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


async def update_role(event, tenant, user):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "event": event,
        "message": "Working on event",
        "tenant": tenant,
    }
    log.debug(log_data)

    if not isinstance(event, list):
        raise Exception("The passed event must be a list.")

    # Let's normalize all of the policies to JSON if they are not already
    for d in event:
        for i in d.get("inline_policies", []):
            if i.get("policy_document") and isinstance(i.get("policy_document"), dict):
                i["policy_document"] = json.dumps(i["policy_document"])

        if d.get("assume_role_policy_document", {}):
            if isinstance(
                d.get("assume_role_policy_document", {}).get(
                    "assume_role_policy_document"
                ),
                dict,
            ):
                d["assume_role_policy_document"][
                    "assume_role_policy_document"
                ] = json.dumps(
                    d["assume_role_policy_document"]["assume_role_policy_document"],
                )

    bad_validation = RoleUpdaterRequest().validate(event, many=True)
    if bad_validation:
        log_data["error"] = bad_validation
        log.error(log_data)
        return {"error_msg": "invalid schema passed", "detail_error": bad_validation}

    event = RoleUpdaterRequest().load(event, many=True)

    result = {"success": False}

    for d in event:
        arn = d["arn"]
        aws_session_name = "noq_roleupdater_" + d["requester"]
        account_number = await parse_account_id_from_arn(arn)
        role_name = await parse_role_name_from_arn(arn)
        # TODO: Make configurable
        client = boto3_cached_conn(
            "iam",
            tenant,
            user,
            account_number=account_number,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": account_number})
            .first.name,
            session_name=sanitize_session_name(aws_session_name),
            retry_max_attempts=2,
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
        )
        inline_policies = d.get("inline_policies", [])
        managed_policies = d.get("managed_policies", [])
        assume_role_doc = d.get("assume_role_policy_document", {})
        tags = d.get("tags", [])

        if (
            not inline_policies
            and not managed_policies
            and not assume_role_doc
            and not tags
        ):
            result["message"] = f"Invalid request. No response taken on event: {event}"
            return result

        try:
            for policy in inline_policies:
                await update_inline_policy(client, role_name, policy)

            for policy in managed_policies:
                await update_managed_policy(client, role_name, policy)

            if assume_role_doc:
                await update_assume_role_document(client, role_name, assume_role_doc)

            for tag in tags:
                await update_tags(client, role_name, tag)
        except ClientError as ce:
            result["message"] = ce.response["Error"]
            result["Traceback"] = traceback.format_exc()
            return result
        result["success"] = True
        return result


async def parse_account_id_from_arn(arn):
    return arn.split(":")[4]


async def parse_role_name_from_arn(arn):
    return arn.split("/")[-1]


async def update_inline_policy(client, role_name, policy):
    log.debug(
        {"message": "Updating inline policy", "role_name": role_name, "policy": policy}
    )
    if policy.get("action") == "attach":
        response = await aio_wrapper(
            client.put_role_policy,
            RoleName=role_name,
            PolicyName=policy["policy_name"],
            PolicyDocument=policy["policy_document"],
        )
    elif policy.get("action") == "detach":
        response = await aio_wrapper(
            client.delete_role_policy,
            RoleName=role_name,
            PolicyName=policy["policy_name"],
        )
    else:
        raise Exception("Unable to update managed policy")
    return response


async def update_managed_policy(client, role_name, policy):
    log.debug(
        {"message": "Updating managed policy", "role_name": role_name, "policy": policy}
    )
    if policy.get("action") == "attach":
        response = await aio_wrapper(
            client.attach_role_policy, PolicyArn=policy["arn"], RoleName=role_name
        )
    elif policy.get("action") == "detach":
        response = await aio_wrapper(
            client.detach_role_policy, PolicyArn=policy["arn"], RoleName=role_name
        )
    else:
        raise Exception("Unable to update managed policy.")
    return response


async def update_assume_role_document(client, role_name, assume_role_doc):
    log.debug(
        {
            "message": "Updating assume role doc",
            "role_name": role_name,
            "assume_role_doc": assume_role_doc,
        }
    )
    response = None
    if assume_role_doc.get("action", "") in ["create", "update"]:
        response = await aio_wrapper(
            client.update_assume_role_policy,
            RoleName=role_name,
            PolicyDocument=assume_role_doc["assume_role_policy_document"],
        )
    return response
    # Log or report result?


async def update_tags(client, role_name, tag):
    log.debug({"message": "Updating tag", "role_name": role_name, "tag": tag})
    if tag.get("action") == "add":
        response = await aio_wrapper(
            client.tag_role,
            RoleName=role_name,
            Tags=[{"Key": tag["key"], "Value": tag["value"]}],
        )
    elif tag.get("action") == "remove":
        response = await aio_wrapper(
            client.untag_role, RoleName=role_name, TagKeys=[tag["key"]]
        )
    else:
        raise Exception("Unable to update tags.")
    return response
