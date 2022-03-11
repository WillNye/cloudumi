import tornado.escape

from common.config import config, ip_restrictions
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class IpRestrictionsHandler(BaseHandler):
    """
    Provides CRUD capabilities to update ip restrictions
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving configured ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access ip restrictions information"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        cidrs = await ip_restrictions.get_ip_restrictions(host)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved IP Restrictions",
            data=cidrs,
            count=len(cidrs),
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        host = self.ctx.host

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Updating ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to update authorized groups tags"
        if not can_admin_all(self.user, self.groups, host):
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
                status="failure",
                status_code=400,
                message="The required body parameter `cidr` was not found in the request",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        await ip_restrictions.set_ip_restriction(host, cidr)

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully updated ip restrictions {cidr}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return

    async def delete(self):
        host = self.ctx.host

        data = tornado.escape.json_decode(self.request.body)
        _cidr = data.get("cidr")

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Deleting ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete ip restrictions"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await ip_restrictions.delete_ip_restriction(host, _cidr)

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

    async def post(self, _enabled):
        host = self.ctx.host

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Toggling ip restrictions",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "enabled": _enabled,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to toggle ip restrictions"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        await ip_restrictions.toggle_ip_restrictions(host, _enabled)

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully toggled ip restrictions {_enabled}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
