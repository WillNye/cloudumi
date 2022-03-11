import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.aws.iam import get_role_managed_policy_documents
from common.lib.aws.unused_permissions_remover import (
    calculate_unused_policy_for_identities,
    calculate_unused_policy_for_identity,
)
from common.models import Status2, WebResponse


class EffectiveRolePolicyHandler(BaseHandler):
    async def get(self, _account_id, _role_name):
        host = self.ctx.host

        effective_identity_permissions = await calculate_unused_policy_for_identity(
            host,
            _account_id,
            _role_name,
            identity_type="role",
        )

        self.write(
            json.loads(
                WebResponse(
                    status=Status2.success,
                    status_code=200,
                    data=effective_identity_permissions,
                ).json(exclude_unset=True, exclude_none=True)
            )
        )
