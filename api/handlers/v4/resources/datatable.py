# import itertools

import tornado.web
from pydantic import BaseModel
from pydantic.fields import Field

from common.config import config
from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseHandler
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.filter import filter_data
from common.models import DataTableResponse

log = config.get_logger()


# TODO: Rebrand as a generic resource provider


class ResourceDataTableModel(BaseModel):
    template_type: str
    identifier: str
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
        tenant = self.ctx.tenant
        tenant_config = TenantConfig(tenant)
        body = tornado.escape.json_decode(self.request.body or "{}")

        redis_key = tenant_config.iambic_templates_redis_key
        template_dicts = await retrieve_json_data_from_redis_or_s3(
            redis_key=redis_key,
            tenant=tenant,
        )
        filtered_templates: DataTableResponse = await filter_data(
            template_dicts, body, model=ResourceDataTableModel
        )
        for template_dict in filtered_templates:
            if "file_path" in template_dict:
                template_dict["file_path"] = template_dict.pop(
                    "repo_relative_file_path", ""
                )
        self.write(filtered_templates.dict())
        await self.finish()
