from tornado.web import Finish

from common.config import config
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.lib.jwt import validate_and_return_jwt_token
from common.lib.tenant.models import TenantDetails
from common.lib.tenant.utils import get_eula
from common.models import EulaModel, TenantDetailsModel, WebResponse


class TenantDetailsHandler(BaseAdminHandler):
    # TODO: Support POST for updated tenant details like membership tier

    async def get(self):
        tenant_details = await TenantDetails.get(self.ctx.tenant)
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=TenantDetailsModel(**tenant_details.dict()).dict(),
            ).json(exclude_unset=True, exclude_none=True)
        )


class TenantEulaHandler(BaseAdminHandler):
    async def post(self):
        tenant = self.ctx.tenant
        tenant_details = await TenantDetails.get(tenant)
        if tenant_details.eula_info:
            self.write(
                WebResponse(
                    status_code=400,
                    reason="The EULA for this tenant has already been signed.",
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(400)
            raise Finish()

        await tenant_details.submit_default_eula(self.user, self.ip)
        self.eula_signed = bool(tenant_details.eula_info)

        # Issue a new JWT with proper groups
        if auth_cookie := self.get_cookie(self.get_noq_auth_cookie_key()):
            res = await validate_and_return_jwt_token(auth_cookie, tenant)

            # Set groups
            await self.set_groups()
            self.groups = list(set(self.groups + res.get("groups_pending_eula", [])))

            # Set roles
            await self.set_eligible_roles(False)
            self.eligible_roles = list(
                set(self.eligible_roles + res.get("additional_roles_pending_eula", []))
            )
        else:
            await self.set_groups()
            await self.set_eligible_roles(False)

        await self.set_jwt_cookie(tenant, self.eligible_roles)

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=TenantDetailsModel(**tenant_details.dict()).dict(),
            ).json(exclude_unset=True, exclude_none=True)
        )


class CognitoTenantPool(TornadoRequestHandler):
    async def get(self):
        tenant = self.get_tenant_name()
        user_pool_region = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_region", tenant, config.region
        )
        if not user_pool_region:
            raise Exception("User pool region is not defined")
        user_pool_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_id", tenant
        )
        if not user_pool_id:
            raise Exception("User pool is not defined")
        client_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_client_id", tenant
        )
        if not client_id:
            raise Exception("Client ID is not defined")

        tenant_details = {
            "client_id": client_id,
            "user_pool_id": user_pool_id,
            "user_pool_region": user_pool_region,
        }
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=tenant_details,
            ).json(exclude_unset=True, exclude_none=True)
        )


class EulaHandler(TornadoRequestHandler):
    async def get(self, version=None):
        eula_text = await get_eula(version)
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=EulaModel(eula=eula_text).dict(),
            ).json(exclude_unset=True, exclude_none=True)
        )
