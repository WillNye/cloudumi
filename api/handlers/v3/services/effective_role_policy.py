import sentry_sdk
import ujson as json

from common.handlers.base import BaseHandler
from common.lib.aws.unused_permissions_remover import (
    calculate_unused_policy_for_identity,
)
from common.models import Status2, WebResponse


class EffectiveRolePolicyHandler(BaseHandler):
    async def get(self, _account_id: str, _role_name: str):
        """Returns the effective policy for an AWS IAM role, which is a minimized and normalized version
        of the role's inline and managed policies. Also returns the effective policy of a role
        which excludes any unused services from the role's permissions, and shell/python commands
        for manually configuring the effective policy.

        :param _account_id: AWS Account ID
        :param _role_name: Role Name
        """
        host = self.ctx.host

        try:
            effective_identity_permissions = await calculate_unused_policy_for_identity(
                host,
                _account_id,
                _role_name,
                identity_type="role",
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            self.write(
                json.loads(
                    WebResponse(status=Status2.error, errors=[str(e)]).json(
                        exclude_unset=True, exclude_none=True
                    )
                )
            )
            return

        self.write(
            json.loads(
                WebResponse(
                    status=Status2.success,
                    status_code=200,
                    data=effective_identity_permissions,
                ).json(exclude_unset=True, exclude_none=True)
            )
        )
