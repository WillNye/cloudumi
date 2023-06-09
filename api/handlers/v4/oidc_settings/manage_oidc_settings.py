import tornado.escape
import tornado.web

from common.config import config
from common.config.models import ModelAdapter
from common.handlers.base import BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dynamo import (  # filter_config_secrets,
    RestrictedDynamoHandler,
    decode_config_secrets,
)
from common.models import (
    AuthSettings,
    GetUserByOIDCSettings,
    OIDCSettingsDto,
    SecretAuthSettings,
    WebResponse,
)

log = config.get_logger()


class ManageOIDCSettingsCrudHandler(BaseHandler):
    """Handler for /api/v4/auth/sso/oidc/?"""

    async def get(self):
        """Retrieve OIDC settings for tenant"""

        # secrets = ModelAdapter(SecretAuthSettings).load_config(
        #     "secrets.auth", self.ctx.tenant, {}
        # )
        # auth = ModelAdapter(AuthSettings).load_config("auth", self.ctx.tenant, {})
        # get_user_by_oidc_settings = ModelAdapter(GetUserByOIDCSettings).load_config(
        #     "get_user_by_oidc_settings", self.ctx.tenant, {}
        # )
        # oidc_settings = OIDCSettingsDto.parse_obj(
        #     {
        #         "get_user_by_oidc_settings": get_user_by_oidc_settings.model,
        #         # ModelAdapter should be able to handle secrets
        #         "secrets": SecretAuthSettings(
        #             **filter_config_secrets(secrets.model.dict(exclude_secrets=False))
        #         ),
        #         "auth": auth.model,
        #     }
        # )

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

        tenant = self.ctx.tenant
        body = tornado.escape.json_decode(self.request.body or "{}")
        body = OIDCSettingsDto.parse_obj(body)
        for obj, model, key in [
            (
                body.get_user_by_oidc_settings,
                GetUserByOIDCSettings,
                "get_user_by_oidc_settings",
            ),
            (body.auth, AuthSettings, "auth"),
            (body.secrets, SecretAuthSettings, "secrets.auth"),
        ]:
            adapter = ModelAdapter(model).load_config(key, tenant, {})
            decoded_data: dict = decode_config_secrets(
                adapter.model.dict(exclude_secrets=False),
                obj.dict(exclude_secrets=False),
            )
            decoded_data = adapter.mode.dict(exclude_secrets=False).update(decoded_data)
            await adapter.from_dict(decoded_data).store_item()

        return self.write(
            WebResponse(
                success="success",
                status_code=200,
            ).dict(exclude_unset=True, exclude_none=True)
        )
