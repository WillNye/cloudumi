from policy_sentry.querying.actions import get_actions_with_access_level
from policy_sentry.querying.all import get_all_service_prefixes

from common.handlers.base import BaseHandler
from common.models import BaseModel, WebResponse


class ListServicesQueryParams(BaseModel):
    service: str = None


class GetServicePermissionsQueryParams(BaseModel):
    resource: str = None


class ListServicesHandler(BaseHandler):
    async def get(self):
        """
        GET /api/v4/aws/services
        """
        query_params = ListServicesQueryParams(
            **{k: self.get_argument(k) for k in self.request.arguments}
        )
        services = get_all_service_prefixes()
        if service_name := query_params.service:
            service_name = service_name.lower()
            services = [s for s in services if service_name in s.lower()]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=services,
            ).json(exclude_unset=True, exclude_none=True)
        )


class GetServicePermissionsHandler(BaseHandler):
    async def get(self, service_name: str, access_level: str):
        """
        GET /api/v4/aws/services/${service_name}/permissions/${access_level}

        Return: list[str]
        """
        # Not using resource param now but we will at some point
        # query_params = GetServicePermissionsQueryParams(
        #     **{k: self.get_argument(k) for k in self.request.arguments}
        # )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=get_actions_with_access_level(service_name, access_level),
            ).json(exclude_unset=True, exclude_none=True)
        )
