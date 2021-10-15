import tornado.escape

from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.lib.auth import can_admin_all
from cloudumi_common.lib.dynamo import UserDynamoHandler
from cloudumi_common.lib.plugins import get_plugin_by_name
from cloudumi_common.lib.web import handle_generic_error_response
from cloudumi_common.models import WebResponse
from cloudumi_identity.lib.groups import (
    Group,
    OktaGroupManagementPlugin,
    OktaIdentityProvider,
)
from cloudumi_identity.lib.groups.models import GroupAttributes

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IdentityGroupHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific group
    """

    async def get(self, _idp, _group_name):
        host = self.ctx.host
        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        # TODO: Authz check? this is a read only endpoint but some companies might not want all employees seeing groups
        group_id = f"{_idp}-{_group_name}"
        ddb = UserDynamoHandler(host)
        matching_group = ddb.identity_groups_table.get_item(
            Key={"host": host, "group_id": group_id}
        )
        if matching_group.get("Item"):
            group = Group.parse_obj(
                ddb._data_from_dynamo_replace(matching_group["Item"])
            )
        else:
            idp_d = config.get_host_specific_key(
                f"site_configs.{host}.identity.identity_providers", host, default={}
            ).get(_idp)
            if not idp_d:
                raise Exception("Invalid IDP specified")
            if idp_d["idp_type"] == "okta":
                idp = OktaIdentityProvider.parse_obj(idp_d)
                idp_plugin = OktaGroupManagementPlugin(host, idp)
            else:
                raise Exception("IDP type is not supported.")
            group = await idp_plugin.get_group(_group_name)
        headers = [
            {"key": "Identity Provider Name", "value": group.idp_name},
            {
                "key": "Group Name",
                "value": group.name,
            },
            {
                "key": "Group Description",
                "value": group.description,
            },
        ]

        group_fields = GroupAttributes.__fields__
        attributes = [
            {
                "name": "requestable",
                "friendly_name": "Requestable",
                "type": "bool",
                "description": group_fields["requestable"].field_info.description,
                "value": group.attributes.requestable,
            },
            {
                "name": "manager_approval_required",
                "friendly_name": "Manager Approval Required",
                "type": "bool",
                "description": group_fields[
                    "manager_approval_required"
                ].field_info.description,
                "value": group.attributes.manager_approval_required,
            },
            {
                "name": "allow_bulk_add_and_remove",
                "friendly_name": "Allow Bulk Add and Removal from Group",
                "type": "bool",
                "description": group_fields[
                    "allow_bulk_add_and_remove"
                ].field_info.description,
                "value": group.attributes.allow_bulk_add_and_remove,
            },
            {
                "name": "approval_chain",
                "friendly_name": "Approvers",
                "type": "array",
                "description": group_fields["approval_chain"].field_info.description,
                "value": group.attributes.approval_chain,
            },
            {
                "name": "self_approval_groups",
                "friendly_name": "Self-Approval Groups",
                "type": "array",
                "description": group_fields[
                    "self_approval_groups"
                ].field_info.description,
                "value": group.attributes.self_approval_groups,
            },
            {
                "name": "emails_to_notify_on_new_members",
                "friendly_name": "Emails to notify when new members are added",
                "type": "array",
                "description": group_fields[
                    "emails_to_notify_on_new_members"
                ].field_info.description,
                "value": group.attributes.emails_to_notify_on_new_members,
            },
        ]
        self.write(
            {
                "headers": headers,
                "group": group.dict(),
                "attributes": attributes,
            }
        )

    async def post(self, _idp, _group_name):
        host = self.ctx.host
        log_data = {
            "function": "IdentityGroupHandler.post",
            "user": self.user,
            "message": "Updating group",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "idp": _idp,
            "group": _group_name,
            "host": host,
        }
        # Checks authz levels of current user
        generic_error_message = "Unable to update group"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)

        idp_d = config.get_host_specific_key(
            f"site_configs.{host}.identity.identity_providers", host, default={}
        ).get(_idp)
        if not idp_d:
            raise Exception("Invalid IDP specified")
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(host, idp)
        else:
            raise Exception("IDP type is not supported.")
        group = await idp_plugin.get_group(_group_name)

        # TODO: Can Pydantic handle this piece for us?
        for k in [
            "approval_chain",
            "self_approval_groups",
            "emails_to_notify_on_new_members",
        ]:
            data[k] = data[k].split(",")

        group.attributes = GroupAttributes.parse_obj(data)

        ddb = UserDynamoHandler(host)
        ddb.identity_groups_table.put_item(
            Item=ddb._data_to_dynamo_replace(group.dict())
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully updated group.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
