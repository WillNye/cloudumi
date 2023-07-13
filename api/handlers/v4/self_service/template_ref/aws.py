import tornado.web

from api.handlers.utils import get_paginated_typeahead_response
from common import Tenant
from common.aws.iam.policy.utils import list_customer_managed_policy_definitions
from common.config import config
from common.exceptions.exceptions import InvalidRequest
from common.handlers.base import BaseHandler
from common.lib.plugins import get_plugin_by_name
from common.models import TypeAheadPaginatedRequestQueryParams, WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


class AWSResourceQueryParams(TypeAheadPaginatedRequestQueryParams):
    resource_id: str = None
    page_size: int = 50


async def handle_aws_resource_template_ref_request(
    tenant: Tenant,
    service: str,
    page: int,
    page_size: int,
    template_id: str = None,
    resource_id: str = None,
    provider_definition_ids: list[str] = None,
) -> list[dict[str, str]]:
    if service == "managed_policy":
        mp_defs = await list_customer_managed_policy_definitions(
            tenant, resource_id, provider_definition_ids
        )
        results = [
            {
                "option_text": mp_def.secondary_resource_id.split("::policy")[1],
                "option_value": str(mp_def.iambic_template_id),
            }
            for mp_def in mp_defs
        ]
    else:
        raise NotImplementedError

    return results[(page - 1) * page_size : page * page_size]


class AWSResourceTemplateRefHandler(BaseHandler):
    async def get(self, service: str = None):
        """
        GET /api/v4/self-service/template-ref/aws/service/${service} - Returns list of matching resource ARNs.
        """
        query_params = AWSResourceQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        try:
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    **get_paginated_typeahead_response(
                        await handle_aws_resource_template_ref_request(
                            self.ctx.db_tenant,
                            service,
                            **query_params.dict(exclude_none=True),
                        ),
                        query_params,
                    ),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except InvalidRequest as err:
            self.set_status(400)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        except Exception as err:
            await log.aexception(
                "Unhandled exception in AWSResourceTemplateRefHandler.get",
                tenant=self.ctx.db_tenant.name,
                query_params=query_params,
            )
            self.set_status(500)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            await log.aexception(
                "Error in AWSResourceTemplateRefHandler",
                tenant=self.ctx.tenant,
            )
            raise tornado.web.Finish()
