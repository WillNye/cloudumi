from typing import Optional

from iambic.plugins.v0_1_0.okta.group.models import OKTA_GROUP_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.okta.user.models import OKTA_USER_TEMPLATE_TYPE

from api.handlers.utils import get_paginated_typeahead_response
from common.config import config
from common.handlers.base import BaseHandler
from common.iambic.templates.utils import list_tenant_templates
from common.lib.plugins import get_plugin_by_name
from common.models import PaginatedRequestQueryParams, WebResponse

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


class OktaUserQueryParams(PaginatedRequestQueryParams):
    email: Optional[str] = None


class OktaUserTypeAheadHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/self-service/typeahead/okta/users - Returns list of matching Okta users.
        """
        query_params = OktaUserQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )

        items = await list_tenant_okta_users(
            self.ctx.db_tenant.id,  # type: ignore
            **query_params.dict(exclude_none=True),
        )

        paginated_items = get_paginated_typeahead_response(
            [user.content.content.get("properties").get("username") for user in items],
            query_params,
        )

        self.set_header("Content-Type", "application/json")

        self.write(
            WebResponse(
                status="success",
                status_code=200,
                reason=None,
                **paginated_items,  # type: ignore
            ).json(exclude_unset=True, exclude_none=True)
        )


class OktaGroupQueryParams(PaginatedRequestQueryParams):
    name: Optional[str] = None


class OktaGroupTypeAheadHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/self-service/typeahead/okta/groups - Returns list of matching Okta groups.
        """
        query_params = OktaGroupQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )

        items = await list_tenant_okta_groups(
            self.ctx.db_tenant.id,  # type: ignore
            **query_params.dict(exclude_none=True),
        )

        paginated_items = get_paginated_typeahead_response(
            [user.content.content.get("properties").get("name") for user in items],
            query_params,
        )

        self.set_header("Content-Type", "application/json")

        self.write(
            WebResponse(
                status="success",
                status_code=200,
                reason=None,
                **paginated_items,  # type: ignore
            ).json(exclude_unset=True, exclude_none=True)
        )


async def list_tenant_okta_users(
    tenant: int,
    email: Optional[str] = None,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
    **kwargs,
) -> list:
    template_type = OKTA_USER_TEMPLATE_TYPE

    templates = await list_tenant_templates(
        tenant_id=tenant,
        template_type=template_type,
        resource_id=email,
        page_size=page_size,
        page=page,
        exclude_template_content=False,
    )

    return templates


async def list_tenant_okta_groups(
    tenant: int,
    name: Optional[str] = None,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
    **kwargs,
) -> list:
    template_type = OKTA_GROUP_TEMPLATE_TYPE

    templates = await list_tenant_templates(
        tenant_id=tenant,
        template_type=template_type,
        resource_id=name,
        page_size=page_size,
        page=page,
        exclude_template_content=False,
    )

    return templates
