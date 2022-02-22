import tornado.escape

from common.config import account, config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()
UNDEFINED = "UNDEFINED"


class HubHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific hub account
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": "HubHandler.get",
            "user": self.user,
            "message": "Retrieving hub information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)

        # Checks authz levels of current user
        generic_error_message = "Cannot access hub account information"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        hub_account_data = await account.get_hub_account(host)

        hub_accounts = [
            {
                "name": "account_name",
                "friendly_name": "Account Name",
                "type": "string",
                "description": "Hub account name",
                "value": hub_account_data.get("name", UNDEFINED),
            },
            {
                "name": "account_id",
                "friendly_name": "Hub Role Account ID",
                "type": "string",
                "description": "Servicing account ID for this hub role",
                "value": hub_account_data.get("account_id", UNDEFINED),
            },
            {
                "name": "role_arn",
                "friendly_name": "Hub Role ARN",
                "type": "string",
                "description": "Servicing hub account arn",
                "value": hub_account_data.get("role_arn", UNDEFINED),
            },
            {
                "name": "external_id",
                "friendly_name": "External ID",
                "type": "array",
                "description": "The External ID used to validate this hub account during authentication",
                "value": hub_account_data.get("external_id", UNDEFINED),
            },
        ]
        self.write(
            {
                "headers": {},
                "count": 1,
                "hub_account": hub_accounts,
                "attributes": {},
            }
        )

    async def post(self):
        host = self.ctx.host

        log_data = {
            "function": "HubHandler.post",
            "user": self.user,
            "message": "Updating hub account role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to update hub account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        name = data.get("name", "")
        account_id = data.get("account_id", "")
        role_name = data.get("role_name", "")
        external_id = data.get("external_id", "")

        await account.set_hub_account(host, name, account_id, role_name, external_id)

        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully updated hub.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return

    async def delete(self):
        host = self.ctx.host

        log_data = {
            "function": "HubHandler.delete",
            "user": self.user,
            "message": "Deleting hub account role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete hub account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await account.delete_hub_account(host)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message="Successfully deleted hub." if deleted else "Unable to delete hub.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class SpokeHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific spoke accounts
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": "SpokeHandler.get",
            "user": self.user,
            "message": "Retrieving spoke information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)

        # Checks authz levels of current user
        generic_error_message = "Cannot access spoke account information"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        spoke_account_data = await account.get_spoke_accounts(host)

        spoke_accounts = [
            [
                {
                    "name": "account_name",
                    "friendly_name": "Account Name",
                    "type": "string",
                    "description": "Hub account name",
                    "value": spoke_account.get("name", UNDEFINED),
                },
                {
                    "name": "account_id",
                    "friendly_name": "Spoke Role Account ID",
                    "type": "string",
                    "description": "Servicing account ID for this spoke role",
                    "value": spoke_account.get("account_id", UNDEFINED),
                },
                {
                    "name": "role_arn",
                    "friendly_name": "Spoke Role ARN",
                    "type": "string",
                    "description": "Servicing spoke account arn",
                    "value": spoke_account.get("role_arn", UNDEFINED),
                },
                {
                    "name": "external_id",
                    "friendly_name": "External ID",
                    "type": "array",
                    "description": "The External ID used to validate this hub account during authentication",
                    "value": spoke_account.get("external_id", UNDEFINED),
                },
            ]
            for spoke_account in spoke_account_data
        ]

        self.write(
            {
                "headers": {},
                "count": len(spoke_accounts),
                "spoke_accounts": spoke_accounts,
                "attributes": {},
            }
        )

    async def post(self):
        host = self.ctx.host

        log_data = {
            "function": "SpokeHandler.post",
            "user": self.user,
            "message": "Updating spoke account role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to update spoke account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        name = data.get("name", "")
        account_id = data.get("account_id", "")
        role_name = data.get("role_name", "")
        external_id = data.get("external_id", "")
        hub_account_name = data.get("hub_account_name", "")

        await account.upsert_spoke_account(
            host, name, account_id, role_name, external_id, hub_account_name
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully updated spoke {name}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class SpokeDeleteHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific spoke accounts
    """

    async def delete(self, _name, _account_id):
        host = self.ctx.host

        log_data = {
            "function": "SpokeHandler.delete",
            "user": self.user,
            "message": "Deleting spoke account role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete hub account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await account.delete_spoke_account(host, _name, _account_id)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message=f"Successfully deleted spoke account {_name}."
            if deleted
            else f"Unable to delete spoke account {_name}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class OrgHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific hub account
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": "OrgHandler.get",
            "user": self.user,
            "message": "Retrieving org information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)

        # Checks authz levels of current user
        generic_error_message = "Cannot access org account information"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        org_account_data = await account.get_org_accounts(host)

        org_accounts = [
            [
                {
                    "name": "org_id",
                    "friendly_name": "Organization's ID",
                    "type": "string",
                    "description": "Organization identifier - uniquely identifies the org",
                    "value": org_account.get("org_id", UNDEFINED),
                },
                {
                    "name": "account_id",
                    "friendly_name": "Org Account ID",
                    "type": "string",
                    "description": "Servicing account ID for this organization",
                    "value": org_account.get("account_id", UNDEFINED),
                },
                {
                    "name": "account_name",
                    "friendly_name": "Organization Account Name",
                    "type": "string",
                    "description": "Servicing org account name",
                    "value": org_account.get("account_name", UNDEFINED),
                },
                {
                    "name": "owner",
                    "friendly_name": "Organization Owner",
                    "type": "array",
                    "description": "The Owner of this Organization",
                    "value": org_account.get("owner", UNDEFINED),
                },
            ]
            for org_account in org_account_data
        ]

        self.write(
            {
                "headers": {},
                "count": len(org_accounts),
                "org_account": org_accounts,
                "attributes": {},
            }
        )

    async def post(self):
        host = self.ctx.host

        log_data = {
            "function": "OrgHandler.post",
            "user": self.user,
            "message": "Updating org account",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to update org for account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        org_id = data.get("org_id", "")
        account_id = data.get("account_id", "")
        account_name = data.get("account_name", "")
        owner = data.get("owner", "")

        await account.upsert_org_account(host, org_id, account_id, account_name, owner)

        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully updated org.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class OrgDeleteHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific hub account
    """

    async def delete(self, _org_id):
        host = self.ctx.host

        log_data = {
            "function": "OrgHandler.delete",
            "user": self.user,
            "message": "Deleting org account role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete org account"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await account.delete_org_account(host, _org_id)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message=f"Successfully deleted org {_org_id}."
            if deleted
            else f"Unable to delete org {_org_id}",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
