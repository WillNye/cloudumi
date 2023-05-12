from common.handlers.base import BaseHandler
from common.iambic.config.utils import (
    list_tenant_provider_definitions,
    list_tenant_providers,
)
from common.lib.pydantic import BaseModel
from common.models import WebResponse


class ProviderDefinitionQueryParams(BaseModel):
    name: str = None
    provider: str = None


class IambicProviderHandler(BaseHandler):
    async def get(self):
        """
        LIST /api/v4/providers - List all providers that are enabled on the tenant’s IAMbic template repo.
        """
        tenant_id = self.ctx.db_tenant.id
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=[
                    {"provider": item.provider, "sub_type": item.sub_type}
                    for item in (await list_tenant_providers(tenant_id))
                ],
            ).json(exclude_unset=True, exclude_none=True)
        )


class IambicProviderDefinitionHandler(BaseHandler):
    async def get(self):
        """
        LIST /api/v4/providers/definitions - List all provider definitions configured for the tenant
        """
        tenant_id = self.ctx.db_tenant.id
        filters = ProviderDefinitionQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        ).dict(exclude_none=True)
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
                        await list_tenant_provider_definitions(tenant_id, **filters)
                    )
                ],
            ).json(exclude_unset=True, exclude_none=True)
        )
