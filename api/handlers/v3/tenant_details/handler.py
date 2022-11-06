from tornado.web import Finish

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
        
        await self.clear_jwt_cookie()

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=TenantDetailsModel(**tenant_details.dict()).dict(),
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
