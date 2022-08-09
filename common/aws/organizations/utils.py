from typing import Dict, Any, Tuple, Set

import boto3

from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.account_indexers.aws_organizations import retrieve_org_structure
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.cache import retrieve_json_data_from_redis_or_s3, store_json_results_in_redis_and_s3
from common.models import OrgAccount, SpokeAccount, HubAccount

log = config.get_logger()


def get_organizations_client(tenant: str, account_id: str, assume_role: str, read_only: bool = True):
    return boto3_cached_conn(
        "organizations",
        tenant,
        None,
        account_number=account_id,
        assume_role=assume_role,
        region=config.region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key(
            "boto3.client_kwargs", tenant, {}
        ),
        session_name=sanitize_session_name("noq_autodiscover_aws_org_accounts"),
        read_only=read_only,
    )


async def get_org_structure(tenant, force_sync=False) -> Dict[str, Any]:
    """Retrieve a dictionary containing the organization structure

    Args:
        force_sync: force a cache update
    """
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_AWS_ORG_STRUCTURE",
    )
    org_structure = await retrieve_json_data_from_redis_or_s3(
        redis_key,
        s3_bucket=config.get_tenant_specific_key(
            "cache_organization_structure.s3.bucket", tenant
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_organization_structure.s3.file",
            tenant,
            "scps/cache_org_structure_v1.json.gz",
        ),
        default={},
        tenant=tenant,
    )
    if force_sync or not org_structure:
        org_structure = await cache_org_structure(tenant)
    return org_structure


async def onboard_new_accounts_from_orgs(tenant: str) -> list[str]:
    log_data = {"function": "onboard_new_accounts_from_orgs", "tenant": tenant}
    new_accounts_onboarded = []
    org_accounts = ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    for org_account in org_accounts:
        if not org_account.automatically_onboard_accounts or not org_account.role_names:
            continue

        spoke_role_name = spoke_accounts.with_query({"account_id": org_account.account_id}).first.name
        org_client = get_organizations_client(tenant, org_account.account_id, spoke_role_name)
        try:
            paginator = org_client.get_paginator("list_accounts")
            for page in paginator.paginate():
                for account in page.get("Accounts"):
                    log_data["account_id"] = account["Id"]
                    if spoke_accounts.query({"account_id": account["Id"]}):
                        log.debug({"message": "Account already in Noq", **log_data})
                        continue  # We already know about this account, and can skip it

                    for aws_organizations_role_name in org_account.role_names:
                        # Get STS client on Org Account
                        # attempt sts:AssumeRole
                        org_role_arn = f"arn:aws:iam::{account['Id']}:role/{aws_organizations_role_name}"
                        log_data["org_role_arn"] = "org_role_arn"
                        try:
                            # TODO: SpokeRoles, by default, do not have the ability to assume other roles
                            # To automatically onboard a new account, we have to grant the Spoke role this capability
                            # temporarily then wait for the permission to propagate. THIS NEEDS TO BE DOCUMENTED
                            # and we need a finally statement to ensure we attempt to remove it.
                            # TODO: Inject retry and/or sleep
                            # TODO: Save somewhere that we know we attempted this account before, so no need to try again.
                            org_sts_client = boto3_cached_conn(
                                "sts",
                                tenant,
                                None,
                                region=config.region,
                                assume_role=spoke_role_name,
                                account_number=org_account.account_id,
                                session_name="noq_onboard_new_accounts_from_orgs",
                            )

                            # Use the spoke role on the org management account to assume into the org role on the
                            # new (unknown) account
                            new_account_credentials = await aio_wrapper(
                                org_sts_client.assume_role,
                                RoleArn=org_role_arn,
                                RoleSessionName="noq_onboard_new_accounts_from_orgs",
                            )

                            new_account_cf_client = await aio_wrapper(
                                boto3.client,
                                "cloudformation",
                                aws_access_key_id=new_account_credentials[
                                    "Credentials"
                                ]["AccessKeyId"],
                                aws_secret_access_key=new_account_credentials[
                                    "Credentials"
                                ]["SecretAccessKey"],
                                aws_session_token=new_account_credentials[
                                    "Credentials"
                                ]["SessionToken"],
                                region_name=config.region,
                            )

                            # Onboard the account.
                            spoke_stack_name = config.get(
                                "_global_.integrations.aws.spoke_role_name",
                                "NoqSpokeRole",
                            )
                            spoke_role_template_url = config.get(
                                "_global_.integrations.aws.registration_spoke_role_cf_template",
                                "https://s3.us-east-1.amazonaws.com/cloudumi-cf-templates/cloudumi_spoke_role.yaml",
                            )
                            spoke_roles = spoke_accounts.models
                            external_id = config.get_tenant_specific_key(
                                "tenant_details.external_id", tenant
                            )
                            if not external_id:
                                log.error(
                                    {**log_data, "error": "External ID not found"}
                                )
                                continue
                            cluster_role = config.get(
                                "_global_.integrations.aws.node_role"
                            )
                            if not cluster_role:
                                log.error(
                                    {**log_data, "error": "Cluster role not found"}
                                )
                                continue
                            if spoke_roles:
                                spoke_role_name = spoke_roles[0].name
                                spoke_stack_name = spoke_role_name
                            else:
                                spoke_role_name = config.get(
                                    "_global_.integrations.aws.spoke_role_name",
                                    "NoqSpokeRole",
                                )
                            hub_account = (
                                ModelAdapter(HubAccount)
                                .load_config("hub_account", tenant)
                                .model
                            )
                            customer_central_account_role = hub_account.role_arn

                            region = config.get(
                                "_global_.integrations.aws.region", "us-west-2"
                            )
                            account_id = config.get(
                                "_global_.integrations.aws.account_id"
                            )
                            cluster_id = config.get("_global_.deployment.cluster_id")
                            registration_topic_arn = config.get(
                                "_global_.integrations.aws.registration_topic_arn",
                                f"arn:aws:sns:{region}:{account_id}:{cluster_id}-registration-topic",
                            )
                            spoke_role_parameters = [
                                {
                                    "ParameterKey": "ExternalIDParameter",
                                    "ParameterValue": external_id,
                                },
                                {
                                    "ParameterKey": "CentralRoleArnParameter",
                                    "ParameterValue": customer_central_account_role,
                                },
                                {
                                    "ParameterKey": "HostParameter",
                                    "ParameterValue": tenant,
                                },
                                {
                                    "ParameterKey": "SpokeRoleNameParameter",
                                    "ParameterValue": spoke_role_name,
                                },
                                {
                                    "ParameterKey": "RegistrationTopicArnParameter",
                                    "ParameterValue": registration_topic_arn,
                                },
                            ]
                            response = new_account_cf_client.create_stack(
                                StackName=spoke_stack_name,
                                TemplateURL=spoke_role_template_url,
                                Parameters=spoke_role_parameters,
                                Capabilities=[
                                    "CAPABILITY_NAMED_IAM",
                                ],
                            )
                            log.debug(
                                {   "message": "Account onboarded successfully.",
                                    "stack_id": response["StackId"],
                                    **log_data,
                                }
                            )
                            new_accounts_onboarded.append(account["Id"])
                            break
                        except Exception as e:
                            log.error({"error": str(e), **log_data}, exc_info=True)
        except Exception as e:
            log.error(f"Unable to retrieve roles from AWS Organizations: {e}")
    return new_accounts_onboarded


async def sync_account_names_from_orgs(tenant: str) -> dict[str, str]:
    log_data = {"function": "sync_account_names_from_orgs", "tenant": tenant}
    org_account_id_to_name = {}
    account_names_synced = {}
    accounts_d: Dict[str, str] = await get_account_id_to_name_mapping(tenant)
    org_account_ids = [
        org.account_id
        for org in ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ]
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    for org_account_id in org_account_ids:
        try:
            spoke_account = spoke_accounts.with_query({"account_id": org_account_id}).first
        except ValueError:
            continue

        org_client = get_organizations_client(tenant, org_account_id, spoke_account.name)
        try:
            paginator = org_client.get_paginator("list_accounts")
            for page in paginator.paginate():
                for account in page.get("Accounts", []):
                    org_account_id_to_name[account["Id"]] = account["Name"]
        except Exception as e:
            log.error({**log_data, "error": str(e)}, exc_info=True)
        for account_id, account_name in accounts_d.items():
            if (
                account_id != account_name
            ):  # The account name was changed from the account ID, don't override it.
                continue  # TODO: Maybe remove this condition?
            if account_id not in org_account_id_to_name:
                continue
            spoke_account_to_replace = spoke_accounts.with_query({"account_id": account_id}).first
            spoke_account_to_replace.account_name = org_account_id_to_name[account_id]
            await spoke_accounts.from_dict(spoke_account_to_replace).with_object_key(
                ["account_id"]
            ).store_item_in_list()
            account_names_synced[account_id] = spoke_account_to_replace.account_name
    return account_names_synced


async def autodiscover_aws_org_accounts(tenant: str) -> set[str]:
    """
    This branch automatically discovers AWS Organization Accounts from Spoke Accounts. It filters out accounts that are
    already flagged as AWS Organization Management Accounts. It also filters out accounts that we've already checked.
    """
    if not config.get_tenant_specific_key(
        "cache_organization_structure.autodiscover_aws_org_accounts", tenant, True
    ):
        return set()

    org_accounts_added = set()
    accounts_d: Dict[str, str] = await get_account_id_to_name_mapping(tenant)
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    org_account_ids = [
        org.account_id
        for org in ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ]
    for account_id in accounts_d.keys():
        if account_id in org_account_ids:
            continue
        try:
            spoke_account = spoke_accounts.with_query({"account_id": account_id}).first
        except ValueError:
            continue

        if spoke_account.org_access_checked:
            continue
        org_client = get_organizations_client(tenant, account_id, spoke_account.name)
        org_details = None
        org_account_name = None
        org_management_account = False
        try:
            org_details = org_client.describe_organization()
            if (
                org_details
                and org_details["Organization"]["MasterAccountId"] == account_id
            ):
                org_management_account = True
                spoke_account.org_management_account = org_management_account
                account_details = org_client.describe_account(AccountId=account_id)
                if account_details:
                    org_account_name = account_details["Account"]["Name"]
        except Exception as e:
            log.error(
                "Unable to retrieve roles from AWS Organizations: {}".format(e),
                exc_info=True,
            )
        spoke_account.org_access_checked = True
        await spoke_accounts.from_dict(spoke_account.dict()).with_object_key(
            ["account_id"]
        ).store_item_in_list()
        if org_management_account and org_details:
            await ModelAdapter(OrgAccount).load_config(
                "org_accounts", tenant
            ).from_dict(
                {
                    "org_id": org_details["Organization"]["Id"],
                    "account_id": account_id,
                    "account_name": org_account_name,
                    "owner": org_details["Organization"]["MasterAccountEmail"],
                }
            ).with_object_key(
                ["org_id"]
            ).store_item_in_list()
            org_accounts_added.add(account_id)
    return org_accounts_added


async def cache_org_structure(tenant: str) -> Dict[str, Any]:
    """Store a dictionary of the organization structure in the cache"""
    all_org_structure = {}
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ):
        org_account_id = organization.account_id
        role_to_assume = spoke_accounts.with_query({"account_id": org_account_id}).first.name
        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Master Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "Noq doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        org_structure = await retrieve_org_structure(
            org_account_id, tenant, role_to_assume=role_to_assume, region=config.region
        )
        all_org_structure.update(org_structure)
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_AWS_ORG_STRUCTURE",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "cache_organization_structure.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "cache_organization_structure.s3.file",
            tenant,
            "scps/cache_org_structure_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        all_org_structure,
        redis_key=redis_key,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
    )
    return all_org_structure


async def _is_member_of_ou(
    identifier: str, ou: Dict[str, Any]
) -> Tuple[bool, Set[str]]:
    """Recursively walk org structure to determine if the account or OU is in the org and, if so, return all OUs of which the account or OU is a member

    Args:
        identifier: AWS account or OU ID
        ou: dictionary representing the organization/organizational unit structure to search
    """
    found = False
    ou_path = set()
    for child in ou.get("Children", []):
        if child.get("Id") == identifier:
            found = True
        elif child.get("Type") == "ORGANIZATIONAL_UNIT":
            found, ou_path = await _is_member_of_ou(identifier, child)
        if found:
            ou_path.add(ou.get("Id"))
            break
    return found, ou_path


async def get_organizational_units_for_account(
    identifier: str,
    tenant: str,
) -> Set[str]:
    """Return a set of Organizational Unit IDs for a given account or OU ID

    Args:
        identifier: AWS account or OU ID
        tenant: Name of the tenant
    """
    all_orgs = await get_org_structure(tenant)
    organizational_units = set()
    for org_id, org_structure in all_orgs.items():
        found, organizational_units = await _is_member_of_ou(identifier, org_structure)
        if found:
            break
    if not organizational_units:
        log.warning("could not find account in organization")
    return organizational_units
