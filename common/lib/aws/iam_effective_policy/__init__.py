import sys

from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import get_role_managed_policy_documents
from common.aws.iam.user.utils import fetch_iam_user
from common.config import config
from common.config.models import ModelAdapter
from common.lib.aws.utils import (
    condense_statements,
    get_account_id_from_arn,
    get_identity_type_from_arn,
)
from common.models import SpokeAccount

log = config.get_logger()


async def calculate_effective_policy_for_identity(
    tenant, arn, managed_policies, force_refresh=False
):
    """
    Calculate the effective policy for a given tenant and arn
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "arn": arn,
        "tenant": tenant,
    }

    account_id = await get_account_id_from_arn(arn)
    identity_type = await get_identity_type_from_arn(arn)
    if identity_type == "role":
        identity = (
            await IAMRole.get(
                tenant, account_id, arn, force_refresh=force_refresh, run_sync=True
            )
        ).dict()
        identity_policy_list_name = "RolePolicyList"
        identity_name_parameter = "RoleName"
    elif identity_type == "user":
        identity = await fetch_iam_user(account_id, arn, tenant, run_sync=True)
        identity_policy_list_name = "UserPolicyList"
        identity_name_parameter = "UserName"
    else:
        raise Exception("Unknown identity type: {}".format(identity_type))

    identity_name = identity["name"]

    spoke_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name
    )
    if not spoke_role_name:
        log.error({**log_data, "message": "No spoke role name found"})
        raise

    # TODO: This is an expensive job. We should pull managed policy details from our cache
    managed_policy_details = get_role_managed_policy_documents(
        {identity_name_parameter: identity_name},
        account_number=account_id,
        assume_role=spoke_role_name,
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        tenant=tenant,
    )
    combined_policy_statements = []
    for policy in identity["policy"].get(identity_policy_list_name, []):
        policy_statements = policy["PolicyDocument"]["Statement"]
        if isinstance(policy_statements, dict):
            policy_statements = [policy_statements]
        combined_policy_statements.extend(policy_statements)

    for policy in identity["policy"]["AttachedManagedPolicies"]:
        policy_statements = managed_policy_details[policy["PolicyName"]]["Statement"]
        if isinstance(policy_statements, dict):
            policy_statements = [policy_statements]
        combined_policy_statements.extend(policy_statements)

    condensed_combined_policy_statements = await condense_statements(
        combined_policy_statements
    )
    return condensed_combined_policy_statements
