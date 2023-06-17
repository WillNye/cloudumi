import tornado.web

from common.handlers.base import BaseHandler
from common.models import BaseModel, WebResponse
from common.request_types.utils import (
    get_tenant_change_type,
    list_tenant_change_types,
    list_tenant_request_types,
)


class SelfServiceRequestTypeParams(BaseModel):
    provider: str = None


class SelfServiceRequestTypeHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/self-service/request-types
        List all supported request types as part of the self-service flow.
        """
        self.set_header("Content-Type", "application/json")
        query_params = SelfServiceRequestTypeParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        tenant_id = self.ctx.db_tenant.id
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=[
                    item.dict()
                    for item in (
                        await list_tenant_request_types(
                            tenant_id, provider=query_params.provider
                        )
                    )
                ],
            ).json(exclude_unset=True, exclude_none=True)
        )


class SelfServiceChangeTypeHandler(BaseHandler):
    async def get(self, request_type_id: str, change_type_id: str = None):
        """
        GET /api/v4/self-service/request-types/{request_type_id}/change-types
        GET /api/v4/self-service/request-types/{request_type_id}/change-types/{change_type_id}

        List or retrieve the supported change type(s) for a request type.
        """
        tenant_id = self.ctx.db_tenant.id
        self.set_header("Content-Type", "application/json")

        if change_type_id:
            change_type = await get_tenant_change_type(tenant_id, change_type_id)
            if not change_type:
                self.write(
                    WebResponse(
                        errors=["Change type not found"],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason="Change type not found")
                raise tornado.web.Finish()
            data = change_type.dict()
            data["fields"] = [
                field.self_service_dict() for field in change_type.change_fields
            ]

        else:
            change_types = await list_tenant_change_types(tenant_id, request_type_id)
            data = [change_type.dict() for change_type in change_types]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=data,
            ).json(exclude_unset=True, exclude_none=True)
        )
