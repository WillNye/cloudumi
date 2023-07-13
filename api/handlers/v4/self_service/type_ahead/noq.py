import tornado.web

from api.handlers.utils import get_paginated_typeahead_response
from common.config import config
from common.groups.utils import list_tenant_groups
from common.handlers.base import BaseHandler
from common.lib.plugins import get_plugin_by_name
from common.models import PaginatedRequestQueryParams, WebResponse
from common.users.utils import list_tenant_users

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger(__name__)


class NoqUserQueryParams(PaginatedRequestQueryParams):
    email: str = None


class NoqGroupQueryParams(PaginatedRequestQueryParams):
    name: str = None


class NoqUserTypeAheadHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/self-service/typeahead/noq/users - Returns list of matching Noq users.
        """
        query_params = NoqUserQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )

        try:
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    **get_paginated_typeahead_response(
                        [
                            user.email
                            for user in (
                                await list_tenant_users(
                                    self.ctx.db_tenant.id,
                                    **query_params.dict(exclude_none=True),
                                )
                            )
                        ],
                        query_params,
                    ),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except Exception as err:
            self.set_status(500)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()


class NoqGroupTypeAheadHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/self-service/typeahead/noq/groups - Returns list of matching Noq users.
        """
        query_params = NoqGroupQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        try:
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    **get_paginated_typeahead_response(
                        [
                            group.name
                            for group in (
                                await list_tenant_groups(
                                    self.ctx.db_tenant.id,
                                    **query_params.dict(exclude_none=True),
                                )
                            )
                        ],
                        query_params,
                    ),
                ).json(exclude_unset=True, exclude_none=True)
            )
        except Exception as err:
            self.set_status(500)
            self.write(
                WebResponse(
                    errors=[repr(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
