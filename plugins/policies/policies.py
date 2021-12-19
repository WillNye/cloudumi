from typing import List

import sentry_sdk

from common.config import config
from common.lib.dynamo import UserDynamoHandler
from common.models import AppDetailsArray, AppDetailsModel, AwsPrincipalModel


class Policies:
    """
    Policies internal plugin
    """

    async def get_errors_by_role(self, arn, host, n=5):
        dynamo = UserDynamoHandler(host=host)
        try:
            return await dynamo.get_top_cloudtrail_errors_by_arn(arn, host, n=n)
        except Exception:
            sentry_sdk.capture_exception()
            return {}

    async def get_applications_associated_with_role(
        self,
        arn: str,
        host: str,
    ) -> AppDetailsArray:
        """
        This function returns applications associated with a role from configuration. You may want to override this
        function to pull this information from an authoratative source.

        :param arn: Role ARN
        :return: AppDetailsArray
        """

        apps_formatted = []

        application_details = config.get_host_specific_key(
            "application_details", host, {}
        )

        for app, details in application_details.items():
            apps_formatted.append(
                AppDetailsModel(
                    name=app,
                    owner=details.get("owner"),
                    owner_url=details.get("owner_url"),
                    app_url=details.get("app_url"),
                )
            )
        return AppDetailsArray(app_details=apps_formatted)

    async def get_roles_associated_with_app(
        self, app_name: str
    ) -> List[AwsPrincipalModel]:
        """
        This function returns roles associated with an app from configuration. You may want to override this
        function to pull this information from an authoritative source.
        :param app_name: Name of application
        :return: List[AwsPrincipalModel]
        """

        return []


def init():
    """Initialize Policies plugin."""
    return Policies()
