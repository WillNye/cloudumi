import tornado.escape
import tornado.web

from common.config import config
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import (
    AuthSettings,
    GetUserBySAMLSettings,
    SAMLSettingsDto,
    WebResponse,
)

log = config.get_logger()


class ManageSAMLSettingsCrudHandler(BaseAdminHandler):
    """Handler for /api/v4/auth/sso/saml/?"""

    async def get(self):
        """Retrieve SAML settings for tenant."""

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )
        auth = AuthSettings(**dynamic_config.get("auth", {}))
        get_user_by_saml_settings = GetUserBySAMLSettings(
            **dynamic_config.get("get_user_by_saml_settings", {})
        )

        oidc_settings = SAMLSettingsDto.parse_obj(
            {
                "get_user_by_saml_settings": get_user_by_saml_settings,
                "auth": auth,
            }
        )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=oidc_settings.dict(
                    exclude_unset=False,
                    exclude_none=False,
                    exclude_secrets=False,
                ),
            ).dict(exclude_unset=True, exclude_none=False, exclude_secrets=False)
        )

    async def post(self):
        """Update SAML settings for tenant."""

        # tenant = self.ctx.tenant
        body = tornado.escape.json_decode(self.request.body or "{}")
        body = SAMLSettingsDto.parse_obj(body)
        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        for obj, model, key in [
            (
                body.get_user_by_saml_settings,
                GetUserBySAMLSettings,
                "get_user_by_saml_settings",
            ),
            (body.auth, AuthSettings, "auth"),
        ]:
            adapter = model(**dynamic_config.get(key, {}))

            dynamic_config.update(
                {
                    key: adapter.dict(
                        exclude_secrets=False, exclude_unset=False, exclude_none=False
                    )
                    | obj.dict(
                        exclude_secrets=False, exclude_unset=False, exclude_none=False
                    )
                }
            )

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config), self.user, self.ctx.tenant
        )

        return self.write(
            WebResponse(
                success="success",
                status_code=200,
            ).dict(exclude_unset=True, exclude_none=True)
        )
