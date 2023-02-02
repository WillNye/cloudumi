from typing import List

import tornado.escape
import tornado.web

from common.handlers.base import BaseHandler
from common.lib.filter import filter_data_with_sqlalchemy
from common.models import WebResponse
from common.role_access.models import RoleAccess


class ManageRoleAccessHandler(BaseHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        tenant_name = self.ctx.tenant

        _filter = data.get("filter", {})

        try:
            objects: List[objects] = await filter_data_with_sqlalchemy(
                _filter, tenant_name, RoleAccess
            )
        except Exception as exc:
            errors = [str(exc)]
            self.write(
                WebResponse(
                    errors=errors,
                    status_code=500,
                    count=len(errors),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            self.set_status(500, reason=str(exc))
            raise tornado.web.Finish()

        res = [x.dict() for x in objects]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"access_roles": res},
            ).dict(exclude_unset=True, exclude_none=True)
        )
