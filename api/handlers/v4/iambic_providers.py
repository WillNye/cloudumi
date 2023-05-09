from common.handlers.base import BaseHandler
from common.iambic.config.utils import (
    list_tenant_provider_definitions,
    list_tenant_providers,
)
from common.models import WebResponse


class IambicProviderHandler(BaseHandler):
    async def get(self):
        """
        LIST /api/v4/providers - List all providers that are enabled on the tenant’s IAMbic template repo.
        """
        tenant = self.ctx.tenant
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=[
                    {"provider": item.provider}
                    for item in (await list_tenant_providers(tenant))
                ],
            ).json(exclude_unset=True, exclude_none=True)
        )


class IambicProviderDefinitionHandler(BaseHandler):
    async def get(self):
        """
        LIST /api/v4/providers/definitions - List all provider definitions configured for the tenant
        """
        tenant = self.ctx.tenant
        filters = {k: self.get_argument(k) for k in self.request.arguments}
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=[
                    {
                        "id": item.id,
                        "name": item.name,
                        "provider": item.provider,
                        "definition": item.definition,
                    }
                    for item in (
                        await list_tenant_provider_definitions(tenant, **filters)
                    )
                ],
            ).json(exclude_unset=True, exclude_none=True)
        )
