import sys
from typing import Any, Dict, List, Literal

import botocore.exceptions
from botocore.exceptions import ClientError

from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.assume_role import ConsoleMeCloudAux
from common.lib.asyncio import aio_wrapper
from common.lib.aws.aws_paginate import aws_paginated
from common.models import (
    CloudAccountModel,
    CloudAccountModelArray,
    OrgAccount,
    ServiceControlPolicyDetailsModel,
    ServiceControlPolicyModel,
    ServiceControlPolicyTargetModel,
    SpokeAccount,
)

log = config.get_logger(__name__)


async def retrieve_accounts_from_aws_organizations(tenant) -> CloudAccountModelArray:
    """
    Polls AWS Organizations for our Account ID to Account Name mapping
    :param: null
    :return: CloudAccountModelArray
    """
    from common.aws.organizations.utils import get_organizations_client

    cloud_accounts = []
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ):
        role_to_assume = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", tenant)
            .with_query({"account_id": organization.account_id})
            .first.name
        )
        if not role_to_assume:
            raise MissingConfigurationValue(
                "Noq doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        if (
            not organization.account_id
        ):  # Consider making this a required field in swagger
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )
        client = get_organizations_client(
            tenant,
            organization.account_id,
            role_to_assume,
        )

        paginator = await aio_wrapper(client.get_paginator, "list_accounts")
        page_iterator = await aio_wrapper(paginator.paginate)
        accounts = []
        for page in page_iterator:
            accounts.extend(page["Accounts"])

        for account in accounts:
            status = account["Status"].lower()
            cloud_accounts.append(
                CloudAccountModel(
                    id=account["Id"],
                    name=account["Name"],
                    email=account["Email"],
                    status=status,
                    type="aws",
                    sync_enabled=True,  # TODO: Check for tag to disable sync?
                )
            )

    return CloudAccountModelArray(accounts=cloud_accounts)


@aws_paginated(
    "Policies",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_service_control_policies(ca: ConsoleMeCloudAux, **kwargs) -> List[Dict]:
    """Return a complete list of service control policy metadata dicts from the paginated ListPolicies API call

    Args:
        ca: ConsoleMeCloudAux instance
    """
    return ca.call(
        "organizations.client.list_policies",
        Filter="SERVICE_CONTROL_POLICY",
        MaxResults=20,
        **kwargs,
    )


async def _transform_organizations_policy_object(policy: Dict) -> Dict:
    """Transform a Policy object returned by an AWS Organizations API to a more convenient format

    Args:
        policy: policy dict returned from organizations:DescribePolicy API
    """
    transformed_policy = policy["PolicySummary"]
    transformed_policy["Content"] = policy["Content"]
    return transformed_policy


async def _get_service_control_policy(ca: ConsoleMeCloudAux, policy_id: str) -> Dict:
    """Retrieve metadata for an SCP by Id, transformed to convenient format. If not found, return an empty dict

    Args:
        ca: ConsoleMeCloudAux instance
        policy_id: Service Control Policy ID
    """
    try:
        result = await aio_wrapper(
            ca.call, "organizations.client.describe_policy", PolicyId=policy_id
        )
    except ClientError as e:
        if (
            e.response["Error"]["Code"] == "400"
            and "PolicyNotFoundException" in e.response["Error"]["Message"]
        ):
            return {}
        raise e
    policy = result.get("Policy")
    return await _transform_organizations_policy_object(policy)


@aws_paginated(
    "Targets",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_targets_for_policy(
    ca: ConsoleMeCloudAux, scp_id: str, **kwargs
) -> List[Dict[str, str]]:
    """Return a complete list of target metadata dicts from the paginated ListTargetsForPolicy API call

    Args:
        ca: ConsoleMeCloudAux instance
        scp_id: service control policy ID
    """
    return ca.call(
        "organizations.client.list_targets_for_policy",
        PolicyId=scp_id,
        MaxResults=20,
        **kwargs,
    )


def _describe_ou(ca: ConsoleMeCloudAux, ou_id: str, **kwargs) -> Dict[str, str]:
    """Wrapper for organizations:DescribeOrganizationalUnit

    Args:
        ca: ConsoleMeCloudAux instance
        ou_id: organizational unit ID
    """
    result = ca.call(
        "organizations.client.describe_organizational_unit",
        OrganizationalUnitId=ou_id,
        **kwargs,
    )
    return result.get("OrganizationalUnit")


def _describe_account(
    ca: ConsoleMeCloudAux, account_id: str, **kwargs
) -> Dict[str, str]:
    """Wrapper for organizations:DescribeAccount

    Args:
        ca: ConsoleMeCloudAux instance
        account_id: AWS account ID
    """
    result = ca.call(
        "organizations.client.describe_account", AccountId=account_id, **kwargs
    )
    return result.get("Account")


@aws_paginated(
    "Children",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_children_for_ou(
    ca: ConsoleMeCloudAux,
    parent_id: str,
    child_type: Literal["ACCOUNT", "ORGANIZATIONAL_UNIT"],
    **kwargs,
) -> List[Dict[str, Any]]:
    """Wrapper for organizations:ListChildren

    Args:
        ca: ConsoleMeCloudAux instance
        parent_id: ID of organization root or organizational unit
        child_type: ACCOUNT or ORGANIZATIONAL_UNIT
    """
    return ca.call(
        "organizations.client.list_children",
        ChildType=child_type,
        ParentId=parent_id,
        **kwargs,
    )


@aws_paginated(
    "Roots",
    response_pagination_marker="NextToken",
    request_pagination_marker="NextToken",
)
def _list_org_roots(ca: ConsoleMeCloudAux, **kwargs) -> List[Dict[str, Any]]:
    """Wrapper for organizations:ListRoots

    Args:
        ca: ConsoleMeCloudAux instance
    """
    return ca.call("organizations.client.list_roots", **kwargs)


def _get_children_for_ou(ca: ConsoleMeCloudAux, root_id: str) -> Dict[str, Any]:
    """Recursively build OU structure

    Args:
        ca: ConsoleMeCloudAux instance
        root_id: ID of organization root or organizational unit
    """
    children: List[Dict[str, Any]] = []
    children.extend(_list_children_for_ou(ca, root_id, "ORGANIZATIONAL_UNIT"))
    children.extend(_list_children_for_ou(ca, root_id, "ACCOUNT"))
    for child in children:
        child["Parent"] = root_id
        if child["Type"] == "ORGANIZATIONAL_UNIT":
            child.update(_describe_ou(ca, child["Id"]))
            child["Children"] = _get_children_for_ou(ca, child["Id"])
        else:
            child.update(_describe_account(ca, child["Id"]))
    return children


async def retrieve_org_structure(
    org_account_id: str,
    tenant,
    role_to_assume: str = "NoqSpokeRole",
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """Retrieve org roots then recursively build a dict of child OUs and accounts.

    This is a slow and expensive operation.

    Args:
        org_account_id: ID for AWS account containing org(s)
        region: AWS region
    """
    conn_details = {
        "assume_role": role_to_assume,
        "account_number": org_account_id,
        "session_name": "noq_scp_sync",
        "region": region,
        "tenant": tenant,
        "client_kwargs": config.get_tenant_specific_key(
            "boto3.client_kwargs", tenant, {}
        ),
    }
    ca = ConsoleMeCloudAux(**conn_details)
    roots = _list_org_roots(ca)
    org_structure = {}
    for root in roots:
        root_id = root["Id"]
        root["Children"] = _get_children_for_ou(ca, root["Id"])
        org_structure[root_id] = root
    return org_structure


async def retrieve_scps_for_organization(
    org_account_id: str,
    tenant: str,
    role_to_assume: str = "NoqSpokeRole",
    region: str = "us-east-1",
) -> List[ServiceControlPolicyModel]:
    """Return a ServiceControlPolicyArrayModel containing all SCPs for an organization

    Args:
        org_account_id: ID for AWS account containing org(s)
        region: AWS region
    """

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "org_account_id": org_account_id,
        "tenant": tenant,
        "role_to_assume": role_to_assume,
        "region": region,
    }

    conn_details = {
        "tenant": tenant,
        "assume_role": role_to_assume,
        "account_number": org_account_id,
        "session_name": "noq_scp_sync",
        "region": region,
        "client_kwargs": config.get_tenant_specific_key(
            "boto3.client_kwargs", tenant, {}
        ),
    }
    ca = ConsoleMeCloudAux(**conn_details)
    all_scp_objects = []
    try:
        all_scp_metadata = await aio_wrapper(_list_service_control_policies, ca)
        for scp_metadata in all_scp_metadata:
            targets = await aio_wrapper(
                _list_targets_for_policy, ca, scp_metadata["Id"]
            )
            policy = await _get_service_control_policy(ca, scp_metadata["Id"])
            target_models = [ServiceControlPolicyTargetModel(**t) for t in targets]
            scp_object = ServiceControlPolicyModel(
                targets=target_models,
                policy=ServiceControlPolicyDetailsModel(**policy),
            )
            all_scp_objects.append(scp_object.dict())
    except botocore.exceptions.ClientError as e:
        log.error(
            {
                **log_data,
                "message": "Unable to get IAM principal owner",
                "error": str(e),
            },
            exc_info=True,
        )
    return all_scp_objects
