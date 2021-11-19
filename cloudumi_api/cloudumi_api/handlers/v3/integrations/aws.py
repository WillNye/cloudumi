from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.models import WebResponse


class AwsIntegrationHandler(BaseHandler):
    """
    AWS Integration Handler
    """

    async def get(self):
        """
        Get AWS Integration
        """
        host = self.ctx.host
        external_id = config.get_host_specific_key(
            f"site_configs.{host}.tenant_details.external_id", host
        )
        if not external_id:
            self.set_status(400)
            res = WebResponse(status_code=400, message="External ID not found")
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        res = WebResponse(
            status="success",
            status_code=200,
            data={
                "cloudformation_url_hub_account": (
                    "https://console.aws.amazon.com/cloudformation/home?region=us-east-1"
                    + "#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-east-1.amazonaws.com"
                    + "%2Fcloudumi-cf-templates%2Fcloudumi_central_role.yaml&"
                    + f"param_ExternalIDParameter={external_id}&param_HostParameter={host}&stackName=cloudumi-iam"
                )
            },
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        """
        Create AWS Integration
        """
        pass
