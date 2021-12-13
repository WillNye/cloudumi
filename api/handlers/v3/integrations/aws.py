import urllib.parse

from common.config import config
from common.handlers.base import BaseHandler
from common.models import WebResponse


class AwsIntegrationHandler(BaseHandler):
    """
    AWS Integration Handler
    """

    async def get(self):
        """
        Get AWS Integration
        """
        host = self.ctx.host
        if not can_admin_all(self.user, self.groups, host):
            self.set_status(403)
            return
        external_id = config.get_host_specific_key(
            f"site_configs.{host}.tenant_details.external_id", host
        )
        if not external_id:
            self.set_status(400)
            res = WebResponse(status_code=400, message="External ID not found")
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        cluster_role = config.get("_global_.aws.node_role")
        if not cluster_role:
            self.set_status(400)
            res = WebResponse(status_code=400, message="Cluster role not found")
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        central_role_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": cluster_role},
                    "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
                    "Action": ["sts:AssumeRole", "sts:TagSession"],
                }
            ],
        }
        registration_queue_arn = config.get(
            "_global_.integrations.aws.registration_sqs_queue_arn",
            "arn:aws:sns:us-east-1:259868150464:noq_registration",
        )
        central_role_template_url = config.get(
            "_global_.integrations.aws.registration_central_role_cf_template",
            "https://s3.us-east-1.amazonaws.com/cloudumi-cf-templates/cloudumi_central_role.yaml",
        )

        spoke_role_template_url = config.get(
            "_global_.integrations.aws.registration_spoke_role_cf_template",
            "https://s3.us-east-1.amazonaws.com/cloudumi-cf-templates/cloudumi_spoke_role.yaml",
        )

        capabilities = ["CAPABILITY_NAMED_IAM"]
        stack_name = config.get(
            "_global_.integrations.aws.central_role_name", "NoqCentralRole"
        )
        spoke_stack_name = config.get(
            "_global_.integrations.aws.spoke_role_name", "NoqSpokeRole"
        )

        central_role_name = config.get(
            "_global_.integrations.aws.central_role_name", "NoqCentralRole"
        )
        spoke_role_name = config.get(
            "_global_.integrations.aws.spoke_role_name", "NoqSpokeRole"
        )
        central_role_parameters = [
            {"ParameterKey": "ExternalIDParameter", "ParameterValue": external_id},
            {"ParameterKey": "HostParameter", "ParameterValue": host},
            {
                "ParameterKey": "ClusterRoleParameter",
                "ParameterValue": cluster_role,
            },
            {
                "ParameterKey": "CentralRoleNameParameter",
                "ParameterValue": central_role_name,
            },
            {
                "ParameterKey": "RegistrationSnsQueArnParameter",
                "ParameterValue": registration_queue_arn,
            },
        ]
        res = WebResponse(
            status="success",
            status_code=200,
            data={
                "central_account_role": {
                    "cloudformation_url": (
                        "https://console.aws.amazon.com/cloudformation/home?region=us-east-1"
                        + "#/stacks/quickcreate?templateURL="
                        + urllib.parse.quote(central_role_template_url)
                        + f"&param_ExternalIDParameter={external_id}&param_HostParameter={host}&stackName={stack_name}"
                        + f"&param_ClusterRoleParameter={cluster_role}"
                        + f"&param_CentralRoleNameParameter={central_role_name}"
                    ),
                    "template_url": central_role_template_url,
                    "stack_name": stack_name,
                    "parameters": central_role_parameters,
                    "external_id": external_id,
                    "node_role": config.get("_global_.aws.node_role"),
                    "role_trust_policy": central_role_trust_policy,
                    "capabilities": capabilities,
                },
                "spoke_account_role": {
                    # We can't configure a customer's spoke roles until their central role is configured, due to the
                    # assume role relationship.
                    "status": "ineligible"
                },
            },
        )

        pre_role_arns_to_assume = config.get_host_specific_key(
            f"site_configs.{host}.policies.pre_role_arns_to_assume", host, []
        )
        if pre_role_arns_to_assume:
            customer_central_account_role = pre_role_arns_to_assume[-1]["role_arn"]
            spoke_role_parameters = [
                {
                    "ParameterKey": "CentralAccountArnParameter",
                    "ParameterValue": customer_central_account_role,
                },
                {"ParameterKey": "HostParameter", "ParameterValue": host},
                {
                    "ParameterKey": "SpokeRoleNameParameter",
                    "ParameterValue": spoke_role_name,
                },
                {
                    "ParameterKey": "RegistrationSnsQueArnParameter",
                    "ParameterValue": registration_queue_arn,
                },
            ]

            spoke_role_trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": customer_central_account_role},
                        "Action": ["sts:AssumeRole", "sts:TagSession"],
                    }
                ],
            }
            res.data["spoke_account_role"] = {
                "status": "eligible",
                "cloudformation_url": (
                    "https://console.aws.amazon.com/cloudformation/home?region=us-east-1"
                    + "#/stacks/quickcreate?templateURL="
                    + urllib.parse.quote(spoke_role_template_url)
                    + f"&param_HostParameter={host}"
                    + f"&param_CentralAccountArnParameter={customer_central_account_role}"
                    + f"&param_SpokeRoleNameParameter={spoke_role_name}"
                    + f"&stackName={spoke_stack_name}"
                ),
                "template_url": spoke_role_template_url,
                "stack_name": spoke_stack_name,
                "parameters": spoke_role_parameters,
                "role_trust_policy": spoke_role_trust_policy,
                "capabilities": capabilities,
            }
        self.write(res.json(exclude_unset=True, exclude_none=True))

    async def post(self):
        """
        Create AWS Integration
        """
        pass
