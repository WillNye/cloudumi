from tornado.web import Finish

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
from common.handlers.base import BaseHandler
from common.iambic_request.request_crud import (
    approve_request,
    create_request,
    create_request_comment,
    delete_request_comment,
    list_requests,
    reject_request,
    request_dict,
    update_request,
    update_request_comment,
)
from common.models import IambicRequest, WebResponse

log = config.get_logger()


class IambicRequestHandler(BaseHandler):
    async def get(self, request_id: str = None):
        """
        GET /api/v4/self-service/request/{request_id} - Get a request by ID
        GET /api/v4/self-service/requests - List all tenant requests with optional filters
        """
        tenant = self.ctx.tenant
        self.set_header("Content-Type", "application/json")

        if request_id:
            try:
                self.write(
                    WebResponse(
                        success="success",
                        status_code=200,
                        data=(await request_dict(tenant, request_id)),
                    ).json(exclude_unset=True, exclude_none=True)
                )
            except NoMatchingRequest as e:
                self.write(
                    WebResponse(
                        error=str(e),
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason=str(e))
                raise Finish()
        else:
            arguments = {k: self.get_argument(k) for k in self.request.arguments}
            filters_url_param = arguments.get("filters", None)
            filters = json.loads(filters_url_param) if filters_url_param else {}
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data=[
                        item.dict() for item in (await list_requests(tenant, **filters))
                    ],
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def post(self):
        """
        POST /api/v4/self-service/requests - Create a new request
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")

        db_tenant = self.ctx.db_tenant
        user = self.user
        request_data = IambicRequest(**json.loads(self.request.body))
        response = await create_request(
            tenant=db_tenant,
            created_by=user,
            justification=request_data.justification,
            changes=request_data.changes,
            request_method="WEB",
        )
        return self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=response.get("friendly_request"),
            ).json(exclude_unset=True, exclude_none=True)
        )

    async def put(self, request_id: str):
        """
        PUT /api/v4/self-service/request/{request_id} - Update a request
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")

        tenant = self.ctx.tenant
        user = self.user
        groups = self.groups
        request_data = IambicRequest(**json.loads(self.request.body))

        try:
            response = await update_request(
                tenant=tenant,
                request_id=request_id,
                updated_by=user,
                updater_groups=groups,
                justification=request_data.justification,
                changes=request_data.changes,
            )
            return self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data=response,
                ).json(exclude_unset=True, exclude_none=True)
            )
        except Unauthorized as e:
            self.set_status(403, reason=str(e))
            return self.write(
                WebResponse(
                    error=str(e),
                    status_code=403,
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def patch(self, request_id: str):
        """
        PATCH /api/v4/self-service/request/{request_id} - Update a request status
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")

        tenant = self.ctx.tenant
        user = self.user
        groups = self.groups
        request_data = json.loads(self.request.body)
        status = request_data.get("status", None)
        if not status:
            err = "The field status must be provided for PATCH"
            self.set_status(400, reason=err)
            return self.write(
                WebResponse(
                    error=err,
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )

        try:
            if status.lower() == "approved":
                response = await approve_request(tenant, request_id, user, groups)
            elif status.lower() == "rejected":
                response = await reject_request(tenant, request_id, user, groups)
            else:
                err = "The status must be either approved or rejected"
                self.set_status(400, reason=err)
                return self.write(
                    WebResponse(
                        error=err,
                        status_code=400,
                    ).json(exclude_unset=True, exclude_none=True)
                )
        except Unauthorized as e:
            self.set_status(403, reason=str(e))
            return self.write(
                WebResponse(
                    error=str(e),
                    status_code=403,
                ).json(exclude_unset=True, exclude_none=True)
            )
        else:
            return self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data=response,
                ).json(exclude_unset=True, exclude_none=True)
            )


class IambicRequestCommentHandler(BaseHandler):
    async def post(self, request_id: str):
        """
        POST /api/v4/self-service/request/{request_id}/comments - Create a new request
        """
        self.set_header("Content-Type", "application/json")
        tenant = self.ctx.tenant
        user = self.user
        try:
            request_data = json.loads(self.request.body)
        except Exception as e:
            log.error(
                {
                    "message": "Error parsing request body",
                    "error": str(e),
                    "request_body": self.request.body,
                },
                exc_info=True,
            )
            self.write(
                WebResponse(
                    errors=["Error parsing request body"],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            return
        await create_request_comment(tenant, request_id, user, request_data.get("body"))
        return self.write(
            WebResponse(
                success="success",
                status_code=200,
            ).json(exclude_unset=True, exclude_none=True)
        )

    async def patch(self, request_id: str, comment_id: str):
        """
        PUT /api/v4/self-service/request/{request_id}/comments/{comment_id} - Update a request
        """
        tenant = self.ctx.tenant
        self.set_header("Content-Type", "application/json")
        user = self.user
        request_data = json.loads(self.request.body)
        try:
            await update_request_comment(
                tenant, comment_id, user, request_data.get("body")
            )
        except Unauthorized as e:
            self.set_status(403, reason=str(e))
            return self.write(
                WebResponse(
                    error=str(e),
                    status_code=403,
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def delete(self, request_id: str, comment_id: str):
        f"""
        DELETE /api/v4/self-service/request/{request_id}/comments/{comment_id} - Delete a request
        """
        self.set_header("Content-Type", "application/json")
        tenant = self.ctx.tenant
        user = self.user
        try:
            await delete_request_comment(tenant, comment_id, user)
        except Unauthorized as e:
            self.set_status(403, reason=str(e))
            return self.write(
                WebResponse(
                    error=str(e),
                    status_code=403,
                ).json(exclude_unset=True, exclude_none=True)
            )
