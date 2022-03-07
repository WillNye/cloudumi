import sentry_sdk
import tornado.escape

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

        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self,
                "unable to update cred brokering",
                errors,
                403,
                "unauthorized",
                log_data,
            )
            return
        log.debug(log_data)

        verb = "enabled" if enabled else "disabled"

        try:
            await role_access.toggle_role_access_credential_brokering(host, enabled)
        except Exception as exc:
            sentry_sdk.capture_exception()
            log.error(exc)
            res = WebResponse(
                success="error",
                status_code=400,
                message=f"Unable to {verb} role access credential brokering.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully {verb} role access credential brokering.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class CredentialBrokeringCurrentStateHandler(BaseHandler):
    """
    Provides CRUD capabilities to enable or disable role access
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": "CredentialBrokeringCurrentStateHandler.get",
            "user": self.user,
            "message": "Retrieving current credential brokering state.",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self,
                "unable to retrieve cred brokering",
                errors,
                403,
                "unauthorized",
                log_data,
            )
            return
        log.debug(log_data)

        current_state = await role_access.get_role_access_credential_brokering(host)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved role access credential brokering.",
            data={"state": current_state},
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class AuthorizedGroupsTagsHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific authorized groups tags
    """

    async def get(self):
        host = self.ctx.host

        log_data = {
            "function": "AuthorizedGroupsTags.get",
            "user": self.user,
            "message": "Retrieving authorized groups tags",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access authorized groups tags information"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        authorized_groups_tags = await role_access.get_authorized_groups_tags(host)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved AuthorizedGroupsTags",
            data=authorized_groups_tags,
            count=len(authorized_groups_tags),
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        host = self.ctx.host

        log_data = {
            "function": "AuthorizedGroupsTags.post",
            "user": self.user,
            "message": "Updating authorized groups tags",
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
        tag_name = data.get("tag_name")
        webaccess = data.get("allow_webconsole_access", False)

        if not tag_name:
            res = WebResponse(
                status="failure",
                status_code=400,
                message="The required body parameter `tag_name` was not found in the request",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        await role_access.upsert_authorized_groups_tag(host, tag_name, webaccess)

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully updated authorized groups tag: {tag_name}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class AuthorizedGroupsTagsDeleteHandler(BaseHandler):
    """
    Provides delete ops for the authorized groups tags
    """

    async def delete(self, _tag_name):
        host = self.ctx.host

        log_data = {
            "function": "AuthorizedGroupsTagsDeleteHandler.delete",
            "user": self.user,
            "tag_name": _tag_name,
            "message": "Deleting authorized groups tags",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete authorized groups tags"
        if not can_admin_all(self.user, self.groups, host):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await role_access.delete_authorized_groups_tag(host, _tag_name)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message=f"Successfully deleted authorized groups tag {_tag_name}."
            if deleted
            else f"Unable to delete authorized groups tag {_tag_name}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
