from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import get_role_managed_policy_documents
from common.aws.iam.user.utils import fetch_iam_user
from common.config import config
from common.lib.aws.utils import (
    condense_statements,
    get_account_id_from_arn,
    get_identity_type_from_arn,
)


async def calculate_effective_policy_for_identity(
    host, arn, managed_policies, force_refresh=False
):
    """
    Calculate the effective policy for a given host and arn
    """
    account_id = await get_account_id_from_arn(arn)
    identity_type = await get_identity_type_from_arn(arn)
    if identity_type == "role":
        identity = (
            await IAMRole.get(
                host, account_id, arn, force_refresh=force_refresh, run_sync=True
            )
        ).dict()
        identity_policy_list_name = "RolePolicyList"
        identity_name_parameter = "RoleName"
    elif identity_type == "user":
        identity = await fetch_iam_user(account_id, arn, host, run_sync=True)
        identity_policy_list_name = "UserPolicyList"
        identity_name_parameter = "UserName"
    else:
        raise Exception("Unknown identity type: {}".format(identity_type))

    identity_name = identity["name"]

    # TODO: This is an expensive job. We should pull managed policy details from our cache
    managed_policy_details = get_role_managed_policy_documents(
        {identity_name_parameter: identity_name},
        account_number=account_id,
        assume_role=config.get_host_specific_key("policies.role_name", host),
        region=config.region,
        retry_max_attempts=2,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        host=host,
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
