from common.config import config
from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dynamo import RestrictedDynamoHandler
from common.models import AuthSettings, Status2, WebResponse

log = config.get_logger()


class AuthSettingsReader(BaseAdminHandler):
    """Handler for /api/v4/auth/sso/"""

    async def get(self):
        """Retrieve AUTH settings for tenant."""
        tenant = TenantConfig.get_instance(self.ctx.tenant)

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )
        auth = AuthSettings(
            **{
                **dynamic_config.get("auth", {}),
                "oidc_redirect_uri": tenant.oidc_redirect_url,
                "scim_enabled": tenant.scim_enabled,
            }  # type: ignore
        )

        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
                data=auth.dict(
                    exclude_unset=False, exclude_none=False, exclude_secrets=False
                ),
            ).dict(exclude_unset=True, exclude_none=True, exclude_secrets=False)
        )
