from typing import List

import tornado.escape
import tornado.web

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.filter import filter_data_with_sqlalchemy
from common.models import WebResponse
from common.role_access.models import RoleAccess

log = config.get_logger()


class ManageRoleAccessHandler(BaseHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)

        _filter = data.get("filter", {})

        try:
            objects: List[objects] = await filter_data_with_sqlalchemy(
                _filter, self.ctx.db_tenant, RoleAccess
            )
        except Exception as exc:
            errors = ["Error while retrieving role access data"]
            self.write(
                WebResponse(
                    errors=errors,
                    status_code=500,
                    count=len(errors),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            log.error(f"Error while retrieving role access data: {exc}", exc_info=True)
            self.set_status(
                500, reason="There was an error retrieving role access data"
            )
            raise

        if len(objects) == 0:
            self.write(
                WebResponse(
                    errors=["No role access data found"],
                    status_code=404,
                    count=len(objects),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            log.warning("No role access data found")
            self.set_status(404, reason="No role access data found")
            raise tornado.web.Finish()

        res = [x.dict() for x in objects]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"access_roles": res},
            ).dict(exclude_unset=True, exclude_none=True)
        )
