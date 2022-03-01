from common.config import config, role_access
from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class CredentialBrokeringHandler(BaseHandler):
    """
    Provides CRUD capabilities to enable or disable role access
    """

    async def post(self, _enabled: str):
        host = self.ctx.host
        enabled = True if _enabled == "enable" else False

        log_data = {
            "function": "RoleAccessHandler.post",
            "user": self.user,
            "message": "Enabling role access" if enabled else "Disabling role access",
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

        verb = "enabled" if enabled else "disabled"

        try:
            await role_access.toggle_role_access_credential_brokering(host, enabled)
        except Exception as exc:
            log.error(exc)
            res = WebResponse(
                success="error",
                status_code=400,
                message=f"Unable to {verb} role access credential brokering.",
            )
        else:
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully {verb} role access credential brokering.",
            )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
