from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.lib.dynamo import UserDynamoHandler
from cloudumi_common.lib.plugins import get_plugin_by_name
from cloudumi_identity.lib.groups import (
    Group,
    OktaGroupManagementPlugin,
    OktaIdentityProvider,
)

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

        group_fields = Group.__fields__
        attributes = [
            {
                "name": "requestable",
                "friendly_name": "Requestable",
                "type": "bool",
                "description": group_fields["requestable"].field_info.description,
            },
            {
                "name": "manager_approval_required",
                "friendly_name": "Manager Approval Required",
                "type": "bool",
                "description": group_fields[
                    "manager_approval_required"
                ].field_info.description,
            },
            {
                "name": "allow_bulk_add_and_remove",
                "friendly_name": "Allow Bulk Add and Removal from Group",
                "type": "bool",
                "description": group_fields[
                    "allow_bulk_add_and_remove"
                ].field_info.description,
            },
            {
                "name": "approval_chain",
                "friendly_name": "Approvers",
                "type": "array",
                "description": group_fields["approval_chain"].field_info.description,
            },
            {
                "name": "self_approval_groups",
                "friendly_name": "Self-Approval Groups",
                "type": "array",
                "description": group_fields[
                    "self_approval_groups"
                ].field_info.description,
            },
            {
                "name": "emails_to_notify_on_new_members",
                "friendly_name": "Emails to notify when new members are added",
                "type": "array",
                "description": group_fields[
                    "emails_to_notify_on_new_members"
                ].field_info.description,
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
            "host": host,
        }
        log.debug(log_data)
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

        group_fields = Group.__fields__
        attributes = [
            {
                "name": "requestable",
                "friendly_name": "Requestable",
                "type": "bool",
                "description": group_fields["requestable"].field_info.description,
            },
            {
                "name": "manager_approval_required",
                "friendly_name": "Manager Approval Required",
                "type": "bool",
                "description": group_fields[
                    "manager_approval_required"
                ].field_info.description,
            },
            {
                "name": "allow_bulk_add_and_remove",
                "friendly_name": "Allow Bulk Add and Removal from Group",
                "type": "bool",
                "description": group_fields[
                    "allow_bulk_add_and_remove"
                ].field_info.description,
            },
            {
                "name": "approval_chain",
                "friendly_name": "Approvers",
                "type": "array",
                "description": group_fields["approval_chain"].field_info.description,
            },
            {
                "name": "self_approval_groups",
                "friendly_name": "Self-Approval Groups",
                "type": "array",
                "description": group_fields[
                    "self_approval_groups"
                ].field_info.description,
            },
            {
                "name": "emails_to_notify_on_new_members",
                "friendly_name": "Emails to notify when new members are added",
                "type": "array",
                "description": group_fields[
                    "emails_to_notify_on_new_members"
                ].field_info.description,
            },
        ]
        self.write(
            {
                "headers": headers,
                "group": group.dict(),
                "attributes": attributes,
            }
        )
