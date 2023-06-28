import sentry_sdk
import tornado.escape

from common.config import config, role_access
from common.handlers.base import BaseHandler
from common.lib.auth import is_tenant_admin
from common.lib.plugins import get_plugin_by_name
from common.lib.web import handle_generic_error_response
from common.models import WebResponse
from common.user_request.utils import get_tra_config

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


class CredentialBrokeringHandler(BaseHandler):
    """
    Provides CRUD capabilities to enable or disable role access
    """

    async def post(self, _access_type: str, _enabled: str):
        tenant = self.ctx.tenant
        enabled = True if _enabled == "enable" else False

        log_data = {
            "function": "RoleAccessHandler.post",
            "user": self.user,
            "message": "Enabling role access" if enabled else "Disabling role access",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        if not is_tenant_admin(self.user, self.groups, tenant):
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
            if _access_type == "tra-access":
                await role_access.toggle_tra_access_credential_brokering(
                    tenant, enabled
                )
            else:
                await role_access.toggle_role_access_credential_brokering(
                    tenant, enabled
                )
        except Exception as exc:
            sentry_sdk.capture_exception()
            log.error(exc)
            res = WebResponse(
                success="error",
                status_code=400,
                message=f"Unable to {verb} {_access_type} credential brokering.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully {verb} {_access_type} credential brokering.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class CredentialBrokeringCurrentStateHandler(BaseHandler):
    """
    Provides CRUD capabilities to enable or disable role access
    """

    async def get(self, _access_type: str):
        tenant = self.ctx.tenant

        log_data = {
            "function": "CredentialBrokeringCurrentStateHandler.get",
            "user": self.user,
            "message": "Retrieving current credential brokering state.",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        if not is_tenant_admin(self.user, self.groups, tenant):
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

        data = {
            "role_access": await role_access.get_role_access_credential_brokering(
                tenant
            ),
            "tra_access": (await get_tra_config(tenant=tenant)).enabled,
        }
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved role access credential brokering.",
            data={**data},
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class AuthorizedGroupsTagsHandler(BaseHandler):
    """
    Provides CRUD capabilities for a specific authorized groups tags
    """

    async def get(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": "AuthorizedGroupsTags.get",
            "user": self.user,
            "message": "Retrieving authorized groups tags",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access authorized groups tags information"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        authorized_groups_tags = await role_access.get_authorized_groups_tags(tenant)
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved AuthorizedGroupsTags",
            data=authorized_groups_tags,
            count=len(authorized_groups_tags),
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": "AuthorizedGroupsTags.post",
            "user": self.user,
            "message": "Updating authorized groups tags",
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
        tag_name = data.get("tag_name")
        webaccess = data.get("allow_webconsole_access", False)

        if not tag_name:
            res = WebResponse(
                status="error",
                status_code=400,
                message="The required body parameter `tag_name` was not found in the request",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        await role_access.upsert_authorized_groups_tag(tenant, tag_name, webaccess)

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
        tenant = self.ctx.tenant

        log_data = {
            "function": "AuthorizedGroupsTagsDeleteHandler.delete",
            "user": self.user,
            "tag_name": _tag_name,
            "message": "Deleting authorized groups tags",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        # Checks authz levels of current user
        generic_error_message = "Unable to delete authorized groups tags"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        deleted = await role_access.delete_authorized_groups_tag(tenant, _tag_name)

        res = WebResponse(
            status="success" if deleted else "error",
            status_code=200 if deleted else 400,
            message=f"Successfully deleted authorized groups tag {_tag_name}."
            if deleted
            else f"Unable to delete authorized groups tag {_tag_name}.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return


class AutomaticRoleTrustPolicyUpdateHandler(BaseHandler):
    """
    Provides a toggle to enable and disable automatic policy updates if NOQ does not have required permissions
    """

    async def get(self):
        tenant = self.ctx.tenant

        log_data = {
            "function": "AutomaticPolicyUpdateHandler.get",
            "user": self.user,
            "message": "Retrieving automatic policy update handler state",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }
        log.debug(log_data)

        generic_error_message = "Cannot access automatic policy update handler state"
        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        log.debug(log_data)

        automatic_update = await role_access.get_role_access_automatic_policy_update(
            tenant
        )
        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully retrieved automatic policy update handler state.",
            data={"enabled": automatic_update},
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self, _enabled: str):
        tenant = self.ctx.tenant
        enabled = True if _enabled == "enable" else False

        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Enabling automatic updates"
            if enabled
            else "Disabling automatic updates",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        if not is_tenant_admin(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self,
                "unable to set automatic updates",
                errors,
                403,
                "unauthorized",
                log_data,
            )
            return
        log.debug(log_data)

        verb = "enabled" if enabled else "disabled"

        try:
            await role_access.toggle_role_access_automatic_policy_update(
                tenant, enabled
            )
        except Exception as exc:
            sentry_sdk.capture_exception()
            log.error(exc)
            res = WebResponse(
                success="error",
                status_code=400,
                message=f"Unable to {verb} role access automatic policy update.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully {verb} role access automatic policy update.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))
        return
