from pydantic import Field

from api.handlers.utils import get_paginated_typeahead_response
from common.handlers.base import BaseHandler
from common.iambic.config.utils import (
    list_tenant_provider_definitions,
    list_tenant_providers,
)
from common.models import PaginatedRequestQueryParams, WebResponse


class ProviderDefinitionQueryParams(PaginatedRequestQueryParams):
    name: str = None
    provider: str = None
    template_id: str = Field(alias="iambic_template_id")


class IambicProviderHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/providers - List all providers that are enabled on the tenant’s IAMbic template repo.
        """
        tenant_id = self.ctx.db_tenant.id
        self.set_header("Content-Type", "application/json")
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
        GET /api/v4/providers/definitions - List all provider definitions configured for the tenant
        """
        tenant_id = self.ctx.db_tenant.id
        query_params = ProviderDefinitionQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        self.set_header("Content-Type", "application/json")
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                **get_paginated_typeahead_response(
                    [
                        item.self_service_dict()
                        for item in (
                            await list_tenant_provider_definitions(
                                tenant_id, **query_params.dict(exclude_none=True)
                            )
                        )
                    ],
                    query_params,
                )
            ).json(exclude_unset=True, exclude_none=True)
        )
