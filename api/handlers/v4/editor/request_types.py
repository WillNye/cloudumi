import traceback
from datetime import datetime

import tornado.web
from pydantic import ValidationError

from common.config import config
from common.handlers.base import BaseAdminHandler, BaseHandler
from common.models import (
    CreateOrPutExpressAccessRequestData,
    PatchChangeTypeData,
    PatchExpressAccessRequestData,
    WebResponse,
)
from common.request_types.models import ChangeType, ExpressAccessRequest
from common.request_types.utils import (
    get_tenant_change_type,
    get_tenant_express_access_request,
)

log = config.get_logger(__name__)


class ExpressAccessRequestEditorHandler(BaseAdminHandler):
    async def get(self, express_access_request_id: str = None):
        """
        GET /api/v4/editor/express-access-requests/{express_access_request_id}
        Get an express access request by ID
        GET /api/v4/editor/express-access-requests
        List all tenant express access requests with optional filters
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)

    async def post(self):
        """
        POST /api/v4/editor/express-access-requests - Create a new express access request
        """
        self.set_header("Content-Type", "application/json")

        db_tenant = self.ctx.db_tenant
        db_user = self.ctx.db_user
        try:
            request_data = CreateOrPutExpressAccessRequestData.parse_raw(
                self.request.body
            )
            express_access_request = await ExpressAccessRequest.create(
                db_tenant.id, db_user, **request_data.dict()
            )
            data = express_access_request.dict()
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(400, reason="ValidationException")
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while creating express access request",
                error=traceback_string,
                tenant_name=db_tenant.name,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data,
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def put(self, express_access_request_id: str):
        """
        PUT /api/v4/editor/express-access-requests/{express_access_request_id} - Update an express access request
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)

    async def patch(self, express_access_request_id: str):
        """
        PATCH /api/v4/editor/express-access-requests/{express_access_request_id} - Update an express access request
        """
        self.set_header("Content-Type", "application/json")

        db_tenant = self.ctx.db_tenant
        db_user = self.ctx.db_user
        try:
            request_data = PatchExpressAccessRequestData.parse_raw(self.request.body)
            express_access_request = await get_tenant_express_access_request(
                db_tenant.id,
                express_access_request_id,
            )
            if not express_access_request:
                reason = "Express access request not found"
                self.write(
                    WebResponse(
                        errors=[reason],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason=reason)
                raise tornado.web.Finish()

            for field, value in request_data.dict(
                exclude_unset=True, exclude_none=True
            ).items():
                setattr(express_access_request, field, value)
            express_access_request.updated_by = db_user.username
            express_access_request.updated_at = datetime.utcnow()
            await express_access_request.write()
            data = express_access_request.dict()
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(400, reason="ValidationException")
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while updating express access request",
                error=traceback_string,
                tenant_name=db_tenant.name,
                express_access_request_id=express_access_request_id,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data,
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def delete(self, express_access_request_id: str):
        """
        DELETE /api/v4/editor/express-access-requests/{express_access_request_id} - Delete an express access request
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)


class ExpressAccessRequestFavoriteHandler(BaseHandler):
    async def post(self, express_access_request_id: str):
        f"""
        POST /api/v4/editor/express-access-request/{express_access_request_id}/favorite
        Favorite or Un-favorite an express access request
        """
        self.set_header("Content-Type", "application/json")

        db_tenant = self.ctx.db_tenant
        db_user = self.ctx.db_user
        try:
            express_access_request = await ExpressAccessRequest.update_favorite_status(
                db_tenant.id, express_access_request_id, db_user
            )
            if not express_access_request:
                reason = "Express access request not found"
                self.write(
                    WebResponse(
                        errors=[reason],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason=reason)
                raise tornado.web.Finish()

            data = express_access_request.self_service_dict()
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(400, reason="ValidationException")
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while updating user favorite status for express access request",
                error=traceback_string,
                tenant_name=db_tenant.name,
                express_access_request_id=express_access_request_id,
                username=db_user.username,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data,
                ).json(exclude_unset=True, exclude_none=True)
            )


class ChangeTypeEditorHandler(BaseAdminHandler):
    async def get(self, change_type_id: str = None):
        """
        GET /api/v4/editor/change-types/{change_type_id}
        Get a change type by ID
        GET /api/v4/editor/change-types
        List all tenant change types with optional filters
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)

    async def post(self):
        """
        POST /api/v4/editor/change-types - Create a new change type
        """
        self.set_header("Content-Type", "application/json")

        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)

    async def put(self, change_type_id: str):
        """
        PUT /api/v4/editor/change-types/{change_type_id} - Update a change type
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)

    async def patch(self, change_type_id: str):
        """
        PATCH /api/v4/editor/change-types/{change_type_id} - Update a change type
        """
        db_tenant = self.ctx.db_tenant
        db_user = self.ctx.db_user
        try:
            request_data = PatchChangeTypeData.parse_raw(self.request.body)
            change_type = await get_tenant_change_type(
                db_tenant.id,
                change_type_id,
            )
            if not change_type:
                reason = "Change type not found"
                self.write(
                    WebResponse(
                        errors=[reason],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason=reason)
                raise tornado.web.Finish()

            for field, value in request_data.dict(
                exclude_unset=True, exclude_none=True
            ).items():
                setattr(change_type, field, value)
            change_type.updated_by = db_user.username
            change_type.updated_at = datetime.utcnow()
            await change_type.write()
            data = change_type.dict()
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(400, reason="ValidationException")
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while patching change type",
                error=traceback_string,
                tenant_name=db_tenant.name,
                change_type_id=change_type_id,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data,
                ).json(exclude_unset=True, exclude_none=True)
            )

    async def delete(self, change_type_id: str):
        """
        DELETE /api/v4/editor/change-types/{change_type_id} - Delete a change type
        """
        reason = "Endpoint not yet implemented"
        self.write(
            WebResponse(
                errors=[reason],
                status_code=404,
            ).json(exclude_unset=True, exclude_none=True)
        )
        self.set_status(404, reason=reason)


class ChangeTypeFavoriteHandler(BaseHandler):
    async def post(self, change_type_id: str):
        f"""
        POST /api/v4/editor/change-types/{change_type_id}/favorite
        Favorite or Un-favorite a change type
        """

        db_tenant = self.ctx.db_tenant
        db_user = self.ctx.db_user
        try:
            change_type = await ChangeType.update_favorite_status(
                db_tenant.id, change_type_id, db_user
            )
            if not change_type:
                reason = "Change type not found"
                self.write(
                    WebResponse(
                        errors=[reason],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason=reason)
                raise tornado.web.Finish()

            data = change_type.self_service_dict()
        except (AssertionError, TypeError, ValidationError) as err:
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=400,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(400, reason="ValidationException")
            return
        except Exception as err:
            # please make sure to only capture traceback string in logs and not
            # send to frontend as a information leak pre-caution
            traceback_string = traceback.format_exc()
            await log.aexception(
                "Unhandled exception while updating user favorite status for change type",
                error=traceback_string,
                tenant_name=db_tenant.name,
                username=db_user.username,
                change_type_id=change_type_id,
            )
            self.write(
                WebResponse(
                    errors=[str(err)],
                    status_code=500,
                ).json(exclude_unset=True, exclude_none=True)
            )
            # reason is in the response header and cannot contain newline
            self.set_status(500, reason="GenericException")
            raise tornado.web.Finish()
        else:
            return self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data=data,
                ).json(exclude_unset=True, exclude_none=True)
            )
