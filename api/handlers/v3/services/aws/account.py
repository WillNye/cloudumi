import tornado.escape

from common.config import account, config
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


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
        # hub_account_data is a special structure, so we unroll it
        hub_accounts = [{x: y for x, y in hub_account_data.items()}]
        self.write(
            {
                "headers": {},
                "count": 1,
                "data": hub_accounts,
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
        role_arn = data.get("role_arn", "")
        external_id = data.get("external_id", "")

        await account.set_hub_account(host, name, account_id, role_arn, external_id)

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
        # spoke_account_data is a special structure, so we unroll it
        spoke_accounts = [
            [
                {x: y for x, y in spoke_account.items()},
            ]
            for spoke_account in spoke_account_data
        ]

        self.write(
            {
                "headers": {},
                "count": len(spoke_accounts),
                "data": spoke_accounts,
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
        role_arn = data.get("role_arn", "")
        external_id = data.get("external_id", "")
        hub_account_arn = data.get("hub_account_arn", "")
        master_for_account = data.get("master_for_account", False)

        await account.upsert_spoke_account(
            host,
            name,
            account_id,
            role_arn,
            external_id,
            hub_account_arn,
            master_for_account,
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
        # org_account_data is a special structure, so we unroll it
        org_accounts = [
            [{x: y for x, y in org_account.items()}] for org_account in org_account_data
        ]

        self.write(
            {
                "headers": {},
                "count": len(org_accounts),
                "data": org_accounts,
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
