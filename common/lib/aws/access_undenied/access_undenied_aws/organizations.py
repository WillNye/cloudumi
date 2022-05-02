import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from aws_error_utils import errors

from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.access_undenied.access_undenied_aws import common, organization_node
from common.lib.aws.access_undenied.access_undenied_aws.organization_node import (
    OrganizationNode,
)
from common.models import SpokeAccount
from util.log import logger

if TYPE_CHECKING:
    from mypy_boto3_organizations import OrganizationsClient
else:
    OrganizationsClient = object


def _deserialize_organization_nodes(
    organization_nodes_object: object,
) -> object:
    if (
        not isinstance(organization_nodes_object, dict)
        or "organization_node_type" not in organization_nodes_object
    ):
        return organization_nodes_object
    return OrganizationNode(
        arn=organization_nodes_object["arn"],
        id_=organization_nodes_object["id"],
        name=organization_nodes_object["name"],
        organization_node_type=organization_nodes_object["organization_node_type"],
        parent=organization_nodes_object["parent"],
        policies=organization_nodes_object["policies"],
    )


def _get_management_account_id(org_client: Any) -> Optional[str]:
    try:
        return (org_client.describe_organization())["Organization"]["MasterAccountId"]
    except errors.AWSOrganizationsNotInUse:
        logger.debug("The account is not a member of an AWS Organization.")
        return None


def _get_management_account_organizations_client(
    config: common.Config,
    management_role_arn: str,
    management_account_id: str,
) -> Optional[OrganizationsClient]:
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.host)
        .with_query({"account_id": config.account_id})
        .first.name
    )
    sts_client = boto3_cached_conn(
        "sts",
        config.host,
        None,
        account_number=config.account_id,
        assume_role=cross_account_role_name,
        region=config.region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    org_client = boto3_cached_conn(
        "organizations",
        config.host,
        None,
        account_number=config.account_id,
        assume_role=cross_account_role_name,
        region=config.region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    if management_account_id == sts_client.get_caller_identity()["Account"]:
        logger.debug("The profile is in the organization's management account.")
        return org_client

    if not management_role_arn:
        return None
    try:
        org_client = boto3_cached_conn(
            "organizations",
            config.host,
            None,
            account_number=management_account_id,
            assume_role=management_role_arn,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
        )
        return org_client
    except errors.AccessDenied:
        logger.error(f"Could not assume organization role: {management_role_arn}")
        return None


def _get_organization_account_nodes(
    management_organizations_client,
) -> Dict[str, organization_node.OrganizationNode]:
    """
    SCPS at different levels of the hierarchy are treated as an AND condition (both must allow).
    Within one level of the hierarchy, different SCPs are treated as an OR (one allow is enough).
    See AWS documentation: Inheritance for service control policies
    https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_inheritance_auth.html
    """
    logger.debug("Traversing organization tree to retrieve all SCPs...")
    organization_root_response = management_organizations_client.list_roots()["Roots"][
        0
    ]
    organization_nodes = {}
    logger.debug(
        "Analyzing SCPs for organization root"
        f" [organization_root: {organization_root_response['Id']}]"
    )
    organization_node_root = organization_node.OrganizationNode(
        arn=organization_root_response["Arn"],
        id_=organization_root_response["Id"],
        name=organization_root_response["Name"],
        organization_node_type="Organizational Unit or Organization Root",
        parent=None,
        policies=_get_target_policies_with_policy_document(
            organization_root_response["Id"], management_organizations_client
        ),
    )
    organization_nodes[organization_root_response["Id"]] = organization_node_root
    organizational_units_stack = [organization_node_root]
    while organizational_units_stack:  # while stack is not empty
        current_organizational_unit = organizational_units_stack.pop()
        for account in management_organizations_client.list_accounts_for_parent(
            ParentId=current_organizational_unit.id
        )["Accounts"]:
            logger.debug(f"Analyzing SCPs for [account_id: {account['Id']}]")
            organization_nodes[account["Id"]] = organization_node.OrganizationNode(
                arn=account["Arn"],
                id_=account["Id"],
                name=account["Name"],
                organization_node_type="AWSAccount",
                parent=current_organizational_unit.id,
                policies=_get_target_policies_with_policy_document(
                    account["Id"], management_organizations_client
                ),
            )

        for (
            organizational_unit_child_response
        ) in management_organizations_client.list_organizational_units_for_parent(
            ParentId=current_organizational_unit.id
        )[
            "OrganizationalUnits"
        ]:
            logger.debug(
                "Analyzing SCPs for [current_organizational_unit"
                f" {organizational_unit_child_response['Id']}]"
            )
            child_organizational_unit_node = organization_node.OrganizationNode(
                arn=organizational_unit_child_response["Arn"],
                id_=organizational_unit_child_response["Id"],
                name=organizational_unit_child_response["Name"],
                organization_node_type="Organizational Unit or Organization Root",
                parent=current_organizational_unit.id,
                policies=_get_target_policies_with_policy_document(
                    organizational_unit_child_response["Id"],
                    management_organizations_client,
                ),
            )
            organization_nodes[
                child_organizational_unit_node.id
            ] = child_organizational_unit_node
            organizational_units_stack.append(child_organizational_unit_node)

    return organization_nodes


def _get_target_policies_with_policy_document(
    target_id: str, management_organizations_client: OrganizationsClient
) -> List[Dict[str, Any]]:
    account_policies: List[
        Dict[str, Any]
    ] = management_organizations_client.list_policies_for_target(
        TargetId=target_id, Filter="SERVICE_CONTROL_POLICY"
    )[
        "Policies"
    ]
    for policy in account_policies:
        policy["PolicyDocument"] = management_organizations_client.describe_policy(
            PolicyId=policy["Id"]
        )["Policy"]["Content"]
    return account_policies


def initialize_organization_data(config: common.Config, scp_file_content: str) -> None:
    cross_account_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", config.host)
        .with_query({"account_id": config.account_id})
        .first.name
    )
    org_client = boto3_cached_conn(
        "organizations",
        config.host,
        None,
        account_number=config.account_id,
        assume_role=cross_account_role_name,
        region=config.region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
    )

    config.management_account_id = _get_management_account_id(org_client)
    if scp_file_content:
        config.organization_nodes = json.loads(
            scp_file_content, object_hook=_deserialize_organization_nodes
        )
        logger.debug(
            "Organization data and SCPs successfully loaded from SCP data" " file..."
        )
        return

    if config.management_account_id:
        management_account_organizations_client = (
            _get_management_account_organizations_client(
                config,
                config.management_account_role_arn,
                config.management_account_id,
            )
        )
        if management_account_organizations_client:
            config.organization_nodes = _get_organization_account_nodes(
                management_account_organizations_client
            )
