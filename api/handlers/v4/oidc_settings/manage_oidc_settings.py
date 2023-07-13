import tornado.escape
import tornado.web

from common.config import config
from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dictutils import delete_in, set_in
from common.lib.dynamo import RestrictedDynamoHandler, decode_config_secrets
from common.lib.yaml import yaml
from common.models import (
    AuthSettings,
    GetUserByOIDCSettings,
    OIDCSettingsDto,
    SecretAuthSettings,
    Status2,
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
            **(dynamic_config.get("get_user_by_oidc_settings") or {})
        )

        oidc_settings = OIDCSettingsDto.parse_obj(
            {
                "get_user_by_oidc_settings": get_user_by_oidc_settings,
                "auth": auth,
            }
        )

        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
                data=oidc_settings.dict(
                    exclude_unset=False,
                    exclude_none=False,
                    exclude_secrets=False,
                ),
            ).dict(exclude_unset=True, exclude_none=False)
        )

    async def post(self):
        """Update OIDC settings for tenant"""

        tenant = TenantConfig.get_instance(self.ctx.tenant)
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
            (
                oidc_setting_dto.auth,
                AuthSettings,
                "auth",
            ),
            (
                oidc_setting_dto.secrets,
                SecretAuthSettings,
                "secrets.auth",
            ),
        ]:
            adapter = model(**(dynamic_config.get(key) or {}))
            upsert = adapter.dict(
                exclude_secrets=False,
                exclude_unset=False,
                exclude_none=False,
            ) | (
                obj.dict(
                    exclude_secrets=False,
                    exclude_unset=False,
                    exclude_none=False,
                )
                if obj is not None
                else {}
            )

            upsert: dict = decode_config_secrets(
                adapter.dict(
                    exclude_secrets=False, exclude_unset=False, exclude_none=False
                ),
                upsert,
            )  # type: ignore

            set_in(dynamic_config, key, upsert)

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
                data=dict(
                    redirect_url=tenant.oidc_redirect_url,
                ),
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        """Delete OIDC settings for tenant"""

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )  # type: ignore

        auth = AuthSettings(**dynamic_config.get("auth", {}))

        if "get_user_by_oidc_settings" in dynamic_config:
            del dynamic_config["get_user_by_oidc_settings"]

        delete_in(dynamic_config, "secrets.auth.oidc")

        auth.get_user_by_oidc = False
        auth.extra_auth_cookies = []
        auth.force_redirect_to_identity_provider = False

        dynamic_config.update(
            {
                "auth": auth.dict(
                    exclude_secrets=False,
                    exclude_unset=False,
                    exclude_none=False,
                )
            }
        )

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
