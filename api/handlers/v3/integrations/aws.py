import urllib.parse

from common.aws.cloud_formations.utils import (
    CF_CAPABILITIES,
    get_cf_aws_cli_cmd,
    get_cf_tf_body,
    get_template_url,
    validate_params,
)
from common.config import config, models
from common.handlers.base import BaseAdminHandler
from common.models import HubAccount, WebResponse


class AwsIntegrationHandler(BaseAdminHandler):
    """
    AWS Integration Handler
    """

    async def get(self):
        """
        Get AWS Integration
        """
        tenant = self.ctx.tenant
        account_name = self.request.arguments.get("account-name", [b""])[0].decode(
            "utf-8"
        )
        try:
            central_role_parameters = await validate_params(
                tenant, "central", account_name=account_name
            )
        except AssertionError as err:
            self.set_status(400)
            res = WebResponse(status_code=400, message=str(err))
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return

        region = config.get("_global_.integrations.aws.region", "us-west-2")
        central_role_template_url = get_template_url("central")
        spoke_role_template_url = get_template_url("spoke")
        external_id = central_role_parameters["ExternalIDParameter"]
        cluster_role = central_role_parameters["ClusterRoleParameter"]
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

        stack_name = config.get(
            "_global_.integrations.aws.central_role_name", "NoqCentralRole"
        )

        central_role_name = central_role_parameters["CentralRoleNameParameter"]
        spoke_role_name = central_role_parameters["SpokeRoleNameParameter"]
        spoke_stack_name = spoke_role_name
        registration_topic_arn = central_role_parameters[
            "RegistrationTopicArnParameter"
        ]

        res = WebResponse(
            status="success",
            status_code=200,
            data={
                "read_write": {
                    "central_account_role": {
                        "cloudformation_url": (
                            f"https://console.aws.amazon.com/cloudformation/home?region={region}"
                            + "#/stacks/quickcreate?templateURL="
                            + urllib.parse.quote(central_role_template_url)
                            + f"&param_ExternalIDParameter={external_id}"
                            + f"&param_AccountNameParameter={account_name}"
                            + f"&param_HostParameter={tenant}"
                            + f"&stackName={stack_name}"
                            + f"&param_ClusterRoleParameter={cluster_role}"
                            + f"&param_CentralRoleNameParameter={central_role_name}"
                            + f"&param_RegistrationTopicArnParameter={registration_topic_arn}"
                            + f"&param_SpokeRoleNameParameter={spoke_role_name}"
                            + "&param_ReadOnlyModeParameter=false"
                        ),
                        "template_url": central_role_template_url,
                        "stack_name": stack_name,
                        "parameters": central_role_parameters,
                        "external_id": external_id,
                        "node_role": config.get("_global_.integrations.aws.node_role"),
                        "role_trust_policy": central_role_trust_policy,
                        "capabilities": CF_CAPABILITIES,
                    },
                    "spoke_account_role": {
                        # We can't configure a customer's spoke roles until their central role is configured, due to the
                        # assume role relationship.
                        "status": "ineligible"
                    },
                    "commands": {
                        "aws": {"central": await get_cf_aws_cli_cmd(tenant, "central")},
                        "terraform": {
                            "central": await get_cf_tf_body(tenant, "central")
                        },
                    },
                },
                "read_only": {
                    "central_account_role": {
                        "cloudformation_url": (
                            f"https://console.aws.amazon.com/cloudformation/home?region={region}"
                            + "#/stacks/quickcreate?templateURL="
                            + urllib.parse.quote(central_role_template_url)
                            + f"&param_ExternalIDParameter={external_id}"
                            + f"&param_AccountNameParameter={account_name}"
                            + f"&param_HostParameter={tenant}"
                            + f"&stackName={stack_name}"
                            + f"&param_ClusterRoleParameter={cluster_role}"
                            + f"&param_CentralRoleNameParameter={central_role_name}"
                            + f"&param_RegistrationTopicArnParameter={registration_topic_arn}"
                            + f"&param_SpokeRoleNameParameter={spoke_role_name}"
                            + "&param_ReadOnlyModeParameter=true"
                        ),
                        "template_url": central_role_template_url,
                        "stack_name": stack_name,
                        "parameters": await validate_params(
                            tenant,
                            "central",
                            read_only_mode=True,
                            account_name=account_name,
                        ),
                        "external_id": external_id,
                        "node_role": config.get("_global_.integrations.aws.node_role"),
                        "role_trust_policy": central_role_trust_policy,
                        "capabilities": CF_CAPABILITIES,
                    },
                    "spoke_account_role": {
                        # We can't configure a customer's spoke roles until their central role is configured, due to the
                        # assume role relationship.
                        "status": "ineligible"
                    },
                    "commands": {
                        "aws": {
                            "central": await get_cf_aws_cli_cmd(tenant, "central", True)
                        },
                        "terraform": {
                            "central": await get_cf_tf_body(tenant, "central", True)
                        },
                    },
                },
            },
        )

        hub_account = (
            models.ModelAdapter(HubAccount).load_config("hub_account", tenant).model
        )
        if hub_account:
            customer_central_account_role = hub_account.role_arn
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

            for account_access in ["read_write", "read_only"]:
                read_only_mode = bool(account_access == "read_only")
                try:
                    spoke_role_parameters = await validate_params(
                        tenant, "spoke", read_only_mode, account_name
                    )
                except AssertionError as err:
                    self.set_status(400)
                    res = WebResponse(status_code=400, message=str(err))
                    self.write(res.json(exclude_unset=True, exclude_none=True))
                    return

                res.data[account_access]["spoke_account_role"] = {
                    "status": "eligible",
                    "cloudformation_url": (
                        f"https://console.aws.amazon.com/cloudformation/home?region={region}"
                        + "#/stacks/quickcreate?templateURL="
                        + urllib.parse.quote(spoke_role_template_url)
                        + f"&param_ExternalIDParameter={external_id}"
                        + f"&param_AccountNameParameter={account_name}"
                        + f"&param_HostParameter={tenant}"
                        + f"&param_CentralRoleArnParameter={customer_central_account_role}"
                        + f"&param_SpokeRoleNameParameter={spoke_role_name}"
                        + f"&stackName={spoke_stack_name}"
                        + f"&param_RegistrationTopicArnParameter={registration_topic_arn}"
                        + f"&param_ReadOnlyModeParameter={str(read_only_mode).lower()}"
                    ),
                    "template_url": spoke_role_template_url,
                    "stack_name": spoke_stack_name,
                    "parameters": spoke_role_parameters,
                    "role_trust_policy": spoke_role_trust_policy,
                    "capabilities": CF_CAPABILITIES,
                    "external_id": external_id,
                }
                res.data[account_access]["commands"]["aws"][
                    "spoke"
                ] = await get_cf_aws_cli_cmd(tenant, "spoke", read_only_mode)
                res.data[account_access]["commands"]["terraform"][
                    "spoke"
                ] = await get_cf_tf_body(tenant, "spoke", read_only_mode)

        self.write(res.json(exclude_unset=True, exclude_none=True))
