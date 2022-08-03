from common.aws.service_config.utils import get_resource_history
from common.aws.utils import ResourceSummary
from common.config import config
from common.exceptions.exceptions import MustBeFte
from common.handlers.base import BaseHandler
from common.models import WebResponse

log = config.get_logger()


class ResourceHistoryHandler(BaseHandler):
    """
    Handler for /api/v3/resource/history/{resourceArn}
    """

    async def get(self, resource_arn: str):
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

        resource_summary = await ResourceSummary.set(tenant, resource_arn)
        resource_history = await get_resource_history(resource_summary)

        res = WebResponse(
            status_code=200,
            data=resource_history,
        )
        self.write(res.json(exclude_unset=True))
