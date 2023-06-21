import tornado.escape
import tornado.web

from common.config import config
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dynamo import RestrictedDynamoHandler, decode_config_secrets
from common.lib.yaml import yaml
from common.models import (
    AuthSettings,
    GetUserByOIDCSettings,
    OIDCSettingsDto,
    SecretAuthSettings,
    WebResponse,
)

log = config.get_logger()


class ManageOIDCSettingsCrudHandler(BaseAdminHandler):
    """Handler for /api/v4/auth/sso/oidc/?"""

    async def get(self):
        """Retrieve OIDC settings for tenant"""

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )
        auth = AuthSettings(**dynamic_config.get("auth", {}))
        get_user_by_oidc_settings = GetUserByOIDCSettings(
            **dynamic_config.get("get_user_by_oidc_settings", {})
        )

        oidc_settings = OIDCSettingsDto.parse_obj(
            {
                "get_user_by_oidc_settings": get_user_by_oidc_settings,
                "auth": auth,
            }
        )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=oidc_settings.dict(
                    exclude_unset=False,
                    exclude_none=True,
                    exclude_secrets=False,
                ),
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def post(self):
        """Update OIDC settings for tenant"""

        # tenant = self.ctx.tenant
        body = tornado.escape.json_decode(self.request.body or "{}")
        oidc_setting_dto = OIDCSettingsDto.parse_obj(body)

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        for obj, model, key in [
            (
                oidc_setting_dto.get_user_by_oidc_settings,
                GetUserByOIDCSettings,
                "get_user_by_oidc_settings",
            ),
            (oidc_setting_dto.auth, AuthSettings, "auth"),
            (oidc_setting_dto.secrets, SecretAuthSettings, "secrets.auth"),
        ]:
            adapter = model(**dynamic_config.get(key, {}))

            upsert = decode_config_secrets(
                adapter.dict(
                    exclude_secrets=False, exclude_unset=False, exclude_none=False
                ),
                adapter.dict(
                    exclude_secrets=False, exclude_unset=False, exclude_none=False
                )
                | obj.dict(
                    exclude_secrets=False, exclude_unset=False, exclude_none=False
                ),
            )
            # update deep keys
            dc = dynamic_config
            for k in key.split("."):
                dc = dc.get(k, {})
            dc.update(upsert)

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config), self.user, self.ctx.tenant
        )

        return self.write(
            WebResponse(
                success="success",
                status_code=200,
            ).dict(exclude_unset=True, exclude_none=True)
        )
