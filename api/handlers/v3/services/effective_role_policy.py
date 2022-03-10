import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.aws.iam import get_role_managed_policy_documents
from common.lib.aws.unused_permissions_remover import (
    calculate_unused_policy_for_identities,
)
from common.models import Status2, WebResponse


class EffectiveRolePolicyHandler(BaseHandler):
    async def get(self, _account_id, _role_name):
        host = self.ctx.host
        arn = f"arn:aws:iam::{_account_id}:role/{_role_name}"

        try:
            managed_policy_details = await sync_to_async(
                get_role_managed_policy_documents
            )(
                {"RoleName": _role_name},
                account_number=_account_id,
                assume_role=config.get_host_specific_key("policies.role_name", host),
                region=config.region,
                retry_max_attempts=2,
                client_kwargs=config.get_host_specific_key(
                    "boto3.client_kwargs", host, {}
                ),
                host=host,
            )
        except Exception:
            sentry_sdk.capture_exception()
            raise

        effective_identity_permissions = await calculate_unused_policy_for_identities(
            host,
            [arn],
            managed_policy_details,
            account_id=_account_id,
        )
        self.write(
            json.loads(
                WebResponse(
                    status=Status2.success,
                    status_code=200,
                    data=effective_identity_permissions[arn],
                ).json(exclude_unset=True, exclude_none=True)
            )
        )
