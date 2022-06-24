import tornado.escape
import ujson as json

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.lib.dynamo import UserDynamoHandler
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse
from identity.lib.groups.groups import get_group_by_name
from identity.lib.groups.models import GroupAttributes, OktaIdentityProvider
from identity.lib.groups.plugins.okta.plugin import OktaGroupManagementPlugin

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IdentityGroupHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific group
    """

    async def get(self, _idp, _group_name):
        tenant = self.ctx.tenant
        log_data = {
            "function": "IdentityGroupHandler.get",
            "user": self.user,
            "message": "Retrieving group information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)
        # TODO: Authz check? this is a read only endpoint but some companies might not want all employees seeing groups
        group = await get_group_by_name(tenant, _idp, _group_name)
        if not group:
            raise Exception("Group not found")
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
                "group": json.loads(group.json()),
                "attributes": attributes,
            }
        )

    async def post(self, _idp, _group_name):
        tenant = self.ctx.tenant
        from common.celery_tasks.celery_tasks import app as celery_app

        log_data = {
            "function": "IdentityGroupHandler.post",
            "user": self.user,
            "message": "Updating group",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "idp": _idp,
            "group": _group_name,
            "tenant": tenant,
        }
        # Checks authz levels of current user
        generic_error_message = "Unable to update group"
        if not can_admin_all(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)

        idp_d = config.get_tenant_specific_key(
            "identity.identity_providers", tenant, default={}
        ).get(_idp)
        if not idp_d:
            raise Exception("Invalid IDP specified")
        if idp_d["idp_type"] == "okta":
            idp = OktaIdentityProvider.parse_obj(idp_d)
            idp_plugin = OktaGroupManagementPlugin(tenant, idp)
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

        ddb = UserDynamoHandler(tenant)
        ddb.identity_groups_table.put_item(
            Item=ddb._data_to_dynamo_replace(json.loads(group.json()))
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully updated group.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_identity_groups_for_tenant_t",
            kwargs={"tenant": tenant},
        )
        return
