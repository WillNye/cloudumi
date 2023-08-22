from typing import Optional

import tornado.web

from common.handlers.base import BaseHandler
from common.models import BaseModel, WebResponse
from common.request_types.utils import (
    get_tenant_change_type,
    list_tenant_request_types,
    self_service_get_tenant_express_access_request,
    self_service_list_tenant_change_types,
    self_service_list_tenant_express_access_requests,
)


class SelfServiceRequestTypeParams(BaseModel):
    provider: str = None


class SelfServiceChangeTypeParams(BaseModel):
    template_type: Optional[str] = None
    boosted_only: Optional[bool] = False


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
                            tenant_id,
                            provider=query_params.provider,
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
            data = change_type.self_service_dict()
            data["fields"] = [
                field.self_service_dict() for field in change_type.change_fields
            ]

        else:
            user_id = self.ctx.db_user.id
            query_params = SelfServiceChangeTypeParams(
                **{k: self.get_argument(k) for k in self.request.arguments}
            )
            change_types = await self_service_list_tenant_change_types(
                tenant_id,
                user_id,
                request_type_id,
                **query_params.dict(),
            )
            data = [change_type.self_service_dict() for change_type in change_types]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=data,
            ).json(exclude_unset=True, exclude_none=True)
        )


class SelfServiceExpressAccessRequestHandler(BaseHandler):
    async def get(self, express_access_request_id: str = None):
        """
        GET /api/v4/self-service/express-access-requests
        GET /api/v4/self-service/express-access-requests/{express_access_request_id}

        List or retrieve the supported change type(s) for a request type.
        """
        tenant_id = self.ctx.db_tenant.id
        user_id = self.ctx.db_user.id
        self.set_header("Content-Type", "application/json")

        if express_access_request_id:
            express_access_request = (
                await self_service_get_tenant_express_access_request(
                    tenant_id, user_id, express_access_request_id
                )
            )
            if not express_access_request:
                self.write(
                    WebResponse(
                        errors=["Express Access Request not found"],
                        status_code=404,
                    ).json(exclude_unset=True, exclude_none=True)
                )
                self.set_status(404, reason="Change type not found")
                raise tornado.web.Finish()

            data = {
                "iambic_template_id": str(express_access_request.iambic_template_id),
                "change_type": express_access_request.change_type.self_service_dict(),
                "provider_definitions": [
                    tpd.tenant_provider_definition.self_service_dict()
                    for tpd in express_access_request.iambic_template_provider_defs
                ],
            }
            change_fields = express_access_request.change_type.change_fields
            if express_access_request.field_values:
                # Override the default value for the change type field
                # with the provided value in the express access request
                change_field_map = {field.field_key: field for field in change_fields}
                for (
                    field_key,
                    default_val,
                ) in express_access_request.field_values.items():
                    change_field_map[field_key].default_value = default_val
                change_fields = list(change_field_map.values())
            data["change_type"]["fields"] = [
                field.self_service_dict() for field in change_fields
            ]
        else:
            query_params = SelfServiceRequestTypeParams(
                **{k: self.get_argument(k) for k in self.request.arguments}
            )
            express_access_requests = (
                await self_service_list_tenant_express_access_requests(
                    tenant_id,
                    user_id,
                    **query_params.dict(exclude_none=True),
                )
            )
            data = [
                express_access_request.self_service_dict()
                for express_access_request in express_access_requests
            ]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=data,
            ).json(exclude_unset=True, exclude_none=True)
        )
