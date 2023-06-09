from typing import Optional

from pydantic import ValidationError

from api.handlers.utils import get_paginated_typeahead_response
from common.handlers.base import BaseHandler
from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.iambic.templates.utils import list_tenant_templates
from common.lib.pydantic import BaseModel
from common.models import PaginatedRequestQueryParams, WebResponse


class IambicTemplateQueryParams(PaginatedRequestQueryParams):
    template_type: Optional[str] = None
    resource_id: Optional[str] = None


class IambicTemplateTypeQueryParams(BaseModel):
    provider: str


class IambicTemplateHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/templates - Provide a summary of all IAMbic templates for the tenant.
        """
        tenant_id = self.ctx.db_tenant.id
        try:
            query_params = IambicTemplateQueryParams(
                **{k: self.get_argument(k) for k in self.request.arguments}
            )
            self.set_header("Content-Type", "application/json")
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
                    ),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except ValidationError as e:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="failure",
                    status_code=400,
                    errors=[str(e)],
                ).json(exclude_unset=True, exclude_none=True)
            )
            return


class IambicTemplateTypeHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/template-types - Provide a summary of all IAMbic templates for the tenant.
        """

        def get_template_type_data(provider_template_classes: list) -> list[dict]:
            provider_template_types = [
                template_type.__fields__["template_type"].default
                for template_type in provider_template_classes
            ]
            return [
                {
                    "id": template_type,
                    "name": template_type.replace(
                        trusted_provider.template_type_prefix, ""
                    ).replace("::", " "),
                }
                for template_type in provider_template_types
            ]

        db_tenant = self.ctx.db_tenant
        try:
            query_params = IambicTemplateTypeQueryParams(
                **{k: self.get_argument(k) for k in self.request.arguments}
            )
            response_data = []

            if query_params.provider:
                trusted_provider = TRUSTED_PROVIDER_RESOLVER_MAP.get(
                    query_params.provider
                )
                if not trusted_provider:
                    raise ValidationError(
                        f"Provider {query_params.provider} is not a valid provider"
                    )
                all_template_types = get_template_type_data(
                    trusted_provider.template_classes
                )
            else:
                all_template_types = []
                for trusted_provider in TRUSTED_PROVIDER_RESOLVER_MAP.values():
                    all_template_types.extend(
                        get_template_type_data(trusted_provider.template_classes)
                    )

            supported_template_types = db_tenant.supported_template_types
            if all_template_types and supported_template_types:
                response_data = [
                    template_type
                    for template_type in all_template_types
                    if template_type["id"] in supported_template_types
                ]

            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data=sorted(response_data, key=lambda d: d["name"]),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except ValidationError as e:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="failure",
                    status_code=400,
                    errors=[str(e)],
                ).json(exclude_unset=True, exclude_none=True)
            )
            return
