import uuid

import tornado.escape

from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dictutils import delete_in, set_in
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import SCIMSettingsDto, Status2, WebResponse


class ScimSettingsHandler(BaseAdminHandler):
    """Handler for /api/v4/auth/sso/scim/?"""

    async def get(self):
        """Retrieve SCIM settings for tenant"""

        tenant_config = TenantConfig.get_instance(self.ctx.tenant)

        scim_enabled = tenant_config.scim_enabled
        scim_url = tenant_config.tenant_url + "/api/v4/scim/v2"

        self.write(
            WebResponse(
                status="success",
                status_code=200,
                reason=None,
                data={
                    "scim_enabled": scim_enabled,
                    "scim_url": scim_url,
                },
            ).dict(exclude_unset=True, exclude_none=False)
        )

    async def post(self):
        """Update SCIM settings for tenant"""

        body = tornado.escape.json_decode(self.request.body or "{}")
        scim_setting_dto = SCIMSettingsDto.parse_obj(body)
        tenant_config = TenantConfig.get_instance(self.ctx.tenant)
        scim_url = tenant_config.tenant_url + "/api/v4/scim/v2"
        scim_enabled = tenant_config.scim_enabled

        if scim_enabled:
            self.set_status(400)
            return self.write(
                WebResponse(
                    status=Status2.error,
                    status_code=400,
                    reason=(
                        "SCIM is already enabled for this tenant. "
                        "Please delete the existing SCIM settings if you wish to regenerate your SCIM token."
                    ),
                    data=None,
                ).dict(exclude_unset=True, exclude_none=True)
            )

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        upsert = (
            scim_setting_dto.dict(
                exclude_secrets=False,
                exclude_unset=False,
                exclude_none=False,
            )
            if scim_setting_dto is not None
            else {}
        )

        new_secret = str(uuid.uuid4())

        set_in(dynamic_config, "scim", upsert.get("scim", False))
        set_in(dynamic_config, "secrets.scim.bearer_token", new_secret)

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )

        return self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
                data={
                    "scim_enabled": scim_setting_dto.scim.enabled,
                    "scim_url": scim_url,
                    "scim_secret": new_secret,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        """Delete SCIM settings for tenant"""

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )  # type: ignore

        if "scim" in dynamic_config:
            del dynamic_config["scim"]

        delete_in(dynamic_config, "secrets.scim")

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )  # type: ignore

        return self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
            ).dict(exclude_unset=True, exclude_none=True)
        )
