from api.handlers.utils import get_paginated_typeahead_response
from common.handlers.base import BaseHandler
from common.iambic.templates.utils import list_tenant_templates
from common.models import PaginatedRequestQueryParams, WebResponse


class IambicTemplateQueryParams(PaginatedRequestQueryParams):
    template_type: str = None
    resource_id: str = None


class IambicTemplateHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/templates - Provide a summary of all IAMbic templates for the tenant.
        """
        tenant_id = self.ctx.db_tenant.id
        query_params = IambicTemplateQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                **get_paginated_typeahead_response(
                    [
                        {
                            "id": item.id,
                            "resource_id": item.resource_id,
                            "resource_type": item.resource_type,
                            "template_type": item.template_type,
                            "provider": item.provider,
                        }
                        for item in (
                            await list_tenant_templates(
                                tenant_id, **query_params.dict(exclude_none=True)
                            )
                        )
                    ],
                    query_params,
                )
            ).json(exclude_unset=True, exclude_none=True)
        )
