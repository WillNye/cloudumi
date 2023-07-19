import traceback

import tornado.web
from pydantic import ValidationError

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import NoMatchingRequest, Unauthorized
from common.handlers.base import BaseHandler
from common.iambic_request.models import Request
from common.iambic_request.request_crud import (
    approve_or_apply_request,
    create_request,
    create_request_comment,
    delete_request_comment,
    get_template_change_for_request,
    list_requests,
    reject_request,
    request_dict,
    run_request_validation,
    update_request,
    update_request_comment,
)
from common.lib.filter import PaginatedQueryResponse, filter_data_with_sqlalchemy
from common.models import SelfServiceRequestData, WebResponse

log = config.get_logger(__name__)


class IambicRequestValidationHandler(BaseHandler):
    async def post(self):
        """
        POST /api/v4/self-service/requests/validate - Create a new request
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")

        db_tenant = self.ctx.db_tenant
        try:
            request_data = SelfServiceRequestData.parse_raw(self.request.body)
            data = await run_request_validation(db_tenant, request_data)
        except (AssertionError, TypeError, ValidationError) as err:
            await log.aexception(
                "Unhandled exception while validating request",
                error=str(err),
                tenant_name=db_tenant.name,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(400, reason=str(err))
            return
        except Exception as err:
            await log.aexception(
                "Unhandled exception while validating user self service request",
                error=str(err),
                tenant_name=db_tenant.name,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(500, reason=str(err))
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data.dict(exclude_none=True),
                ).json(exclude_unset=True, exclude_none=True)
            )


class IambicRequestHandler(BaseHandler):
    async def get(self, request_id: str = None):
        """
        GET /api/v4/self-service/requests/{request_id} - Get a request by ID
        GET /api/v4/self-service/requests - List all tenant requests with optional filters
        """
        db_tenant = self.ctx.db_tenant
        self.set_header("Content-Type", "application/json")

        if request_id:
            try:
                self.write(
                    WebResponse(
                        success="success",
                        status_code=200,
                        data=(await request_dict(db_tenant, request_id)),
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
                return
        else:
            arguments = {k: self.get_argument(k) for k in self.request.arguments}
            filters_url_param = arguments.get("filters", None)
            filters = json.loads(filters_url_param) if filters_url_param else {}
            self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=[
                        item.dict()
                        for item in (await list_requests(db_tenant.id, **filters))
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
        try:
            request_data = SelfServiceRequestData.parse_raw(self.request.body)
            template_change = await get_template_change_for_request(
                db_tenant, request_data
            )
            response = await create_request(
                tenant=db_tenant,
                created_by=user,
                justification=request_data.justification,
                changes=[template_change],
                request_method="WEB",
            )
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(400, reason=str(err))
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while creating user self service request",
                error=traceback_string,
                tenant_name=db_tenant.name,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(500, reason=str(err))
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=response.get("friendly_request"),
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def put(self, request_id: str):
        """
        PUT /api/v4/self-service/requests/{request_id} - Update a request
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")
        db_tenant = self.ctx.db_tenant
        user = self.user
        groups = self.groups
        request_data = SelfServiceRequestData.parse_raw(self.request.body)

        try:
            template_change = await get_template_change_for_request(
                db_tenant, request_data
            )
            response = await update_request(
                tenant=db_tenant,
                request_id=request_id,
                updated_by=user,
                updater_groups=groups,
                justification=request_data.justification,
                changes=[template_change],
            )
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=response["friendly_request"],
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
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(400, reason=str(err))
            return
        except Exception as err:
            await log.aexception(
                "Unhandled exception while validating request", tenant=db_tenant.name
            )
            self.set_status(500, reason=str(err))
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

    async def patch(self, request_id: str):
        """
        PATCH /api/v4/self-service/requests/{request_id} - Update a request status
        """
        await self.fte_check()
        self.set_header("Content-Type", "application/json")
        db_tenant = self.ctx.db_tenant
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
            if status.lower() in {"approved", "apply"}:
                apply_request = status.lower() == "apply"
                response = await approve_or_apply_request(
                    db_tenant, request_id, user, groups, apply_request
                )
            elif status.lower() == "rejected":
                response = await reject_request(db_tenant, request_id, user, groups)
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
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(400, reason=str(err))
            return
        except Exception as err:
            await log.aexception(
                "Unhandled exception while validating request", tenant=db_tenant.name
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            self.set_status(500, reason=str(err))
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=response,
                ).json(exclude_unset=True, exclude_none=True)
            )


class IambicRequestCommentHandler(BaseHandler):
    async def post(self, request_id: str):
        """
        POST /api/v4/self-service/requests/{request_id}/comments - Create a new request
        """
        self.set_header("Content-Type", "application/json")
        db_tenant = self.ctx.db_tenant
        user = self.user
        try:
            request_data = json.loads(self.request.body)
        except Exception:
            await log.aerror(
                "Error parsing request body",
                tenant_name=db_tenant.name,
                request_body=self.request.body,
                exc_info=True,
            )
            self.write(
                WebResponse(
                    errors=["Error parsing request body"],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            return
        await create_request_comment(
            db_tenant.id, request_id, user, request_data.get("comment")
        )
        self.set_status(204)

    async def patch(self, request_id: str, comment_id: str):
        """
        PUT /api/v4/self-service/requests/{request_id}/comments/{comment_id} - Update a request
        """
        self.set_header("Content-Type", "application/json")
        db_tenant = self.ctx.db_tenant
        user = self.user
        request_data = json.loads(self.request.body)
        try:
            await update_request_comment(
                db_tenant.id, comment_id, user, request_data.get("body")
            )
            self.set_status(204)
            return self.write(
                WebResponse(
                    status_code=204,
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

    async def delete(self, request_id: str, comment_id: str):
        f"""
        DELETE /api/v4/self-service/requests/{request_id}/comments/{comment_id} - Delete a request
        """
        self.set_header("Content-Type", "application/json")
        db_tenant = self.ctx.db_tenant
        user = self.user
        try:
            await delete_request_comment(db_tenant.id, comment_id, user)
            self.set_status(204)
            return self.write(
                WebResponse(
                    status_code=204,
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


class IambicRequestDataTableHandler(BaseHandler):
    async def post(self):
        """
        POST /api/v4/self-service/requests/datatable - Retrieve a filtered list of requests
        """
        data = tornado.escape.json_decode(self.request.body)
        tenant = self.ctx.db_tenant
        try:
            query_response: PaginatedQueryResponse = await filter_data_with_sqlalchemy(
                data, tenant, Request
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
            self.set_status(500, reason=str(exc))
            raise tornado.web.Finish()

        query_response.data = [
            json.loads(json.dumps(x.dict())) for x in query_response.data
        ]
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=query_response.dict(exclude_unset=True, exclude_none=True),
            ).dict(exclude_unset=True, exclude_none=True)
        )
