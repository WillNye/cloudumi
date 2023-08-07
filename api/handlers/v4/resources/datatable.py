from typing import Optional

import tornado.web
from pydantic import BaseModel
from pydantic.fields import Field

from common.config import config
from common.handlers.base import BaseHandler
from common.iambic.templates.utils import tenant_templates_datatable
from common.lib.filter import FilterModel, PaginatedQueryResponse
from common.models import WebResponse

log = config.get_logger(__name__)


# TODO: Rebrand as a generic resource provider


class ResourceDataTableModel(BaseModel):
    template_type: str
    identifier: Optional[str]
    repo_name: str
    repo_relative_file_path: str = Field(..., alias="file_path")
    provider: str = "IAMbic"


class ResourcesDataTableHandler(BaseHandler):
    """Handler for /api/v4/resources/datatable/

    Api endpoint to list and filter resources, including IAMbic templates
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v4/resources/datatable/
        """
        data = tornado.escape.json_decode(self.request.body)
        tenant = self.ctx.db_tenant
        try:
            query_response: PaginatedQueryResponse = await tenant_templates_datatable(
                tenant.id, FilterModel.parse_obj(data)
            )
        except Exception as exc:
            errors = [str(exc)]
            await log.aexception(
                "Unhandled exception in IambicRequestDataTableHandler.post",
                tenant=tenant.name,
                data=data,
            )
            self.write(
                WebResponse(
                    errors=errors,
                    status_code=500,
                    count=len(errors),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()

        query_response.data = [
            dict(
                repo_name=provider_template.iambic_template.repo_name,
                file_path=provider_template.iambic_template.file_path,
                template_type=provider_template.iambic_template.template_type,
                resource_id=provider_template.resource_id,
                secondary_resource_id=provider_template.secondary_resource_id,
                provider=provider_template.iambic_template.provider,
            )
            for provider_template in query_response.data
        ]
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=query_response.dict(exclude_unset=True, exclude_none=True),
            ).dict(exclude_unset=True, exclude_none=True)
        )
