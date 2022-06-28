import sentry_sdk

from common.config import config
from common.exceptions.exceptions import MustBeFte
from common.handlers.base import BaseAPIV2Handler
from common.lib.aws.utils import get_scps_for_account_or_ou
from common.models import Status2, WebResponse

log = config.get_logger()


class ServiceControlPolicyHandler(BaseAPIV2Handler):
    """
    Handler for /api/v2/service_control_policies/{accountNumberOrOuId}

    Returns Service Control Policies targeting specified account or OU
    """

    allowed_methods = ["GET"]

    async def get(self, identifier):
        tenant = self.ctx.tenant
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                tenant,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        log_data = {
            "function": "ServiceControlPolicyHandler.get",
            "user": self.user,
            "message": "Retrieving service control policies for identifier",
            "identifier": identifier,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant,
        }

        log.debug(log_data)
        try:
            scps = await get_scps_for_account_or_ou(identifier, tenant)
        except Exception as e:
            sentry_sdk.capture_exception()
            response = WebResponse(
                status=Status2.error, status_code=403, errors=[str(e)], data=[]
            )
            self.write(response.json())
            return
        response = WebResponse(
            status=Status2.success, status_code=200, data=scps.__root__
        )
        self.write(response.json())
