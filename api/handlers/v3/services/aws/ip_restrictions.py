import ipaddress

import tornado.escape

from common.config import config, ip_restrictions
from common.handlers.base import BaseHandler
from common.lib.auth import is_tenant_admin
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()
log = config.get_logger()


class IpRestrictionsHandler(BaseHandler):
    """
    Provides CRUD capabilities to update ip restrictions
    """

    async def get(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving configured ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access ip restrictions information"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        cidrs = await ip_restrictions.get_ip_restrictions(tenant)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved IP Restrictions",
            data=cidrs,
            count=len(cidrs),
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Updating ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to update authorized groups tags"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        data = tornado.escape.json_decode(self.request.body)
        cidr = data.get("cidr")

        if not cidr:
            res = WebResponse(
                status="error",
                status_code=400,
                message="The required body parameter `cidr` was not found in the request",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        try:
            ipaddress.ip_network(cidr)
        except ValueError as e:
            res = WebResponse(
                status="error",
                status_code=400,
                message=f"The required body parameter `cidr` is not a valid IP CIDR: {str(e)}",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        await ip_restrictions.set_ip_restriction(tenant, cidr)

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully updated ip restrictions {cidr}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return

    async def delete(self):
        tenant = self.ctx.tenant

        data = tornado.escape.json_decode(self.request.body)
        _cidr = data.get("cidr")

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Deleting ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete ip restrictions"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await ip_restrictions.delete_ip_restriction(tenant, _cidr)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message=f"Successfully deleted ip restrictions {_cidr}."
            if deleted
            else f"Unable to delete ip restrictions {_cidr}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class IpRestrictionsToggleHandler(BaseHandler):
    """
    Provides a toggle handler for ip restrictions
    """

    async def get(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving configured ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access ip restrictions toggle"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        enabled = await ip_restrictions.get_ip_restrictions_toggle(tenant)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved IP Restrictions Toggle",
            data={"enabled": enabled},
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self, _enabled):
        tenant = self.ctx.tenant

        enabled = _enabled == "enable"

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Toggling ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "enabled": _enabled,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to toggle ip restrictions"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        await ip_restrictions.toggle_ip_restrictions(tenant, enabled)

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully toggled ip restrictions to: {enabled}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class IpRestrictionsRequesterIpOnlyToggleHandler(BaseHandler):
    """
    Provides a toggle handler to restrict credentials to requesters IP
    """

    async def get(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving configured ip restrictions toggle on requester ip only",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access ip restrictions toggle"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        enabled = await ip_restrictions.get_ip_restrictions_on_requester_ip_only_toggle(
            tenant
        )
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved IP Restrictions requester ip only toggle",
            data={"enabled": enabled},
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self, _enabled):
        tenant = self.ctx.tenant

        enabled = _enabled == "enable"

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": f"Toggling ip restrictions on requester {self.ip}",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "enabled": enabled,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to toggle ip restrictions"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        await ip_restrictions.toggle_ip_restrictions_on_requester_ip_only(
            tenant, _enabled
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully toggled ip restrictions {enabled}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
