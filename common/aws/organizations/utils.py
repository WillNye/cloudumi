import sys
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set, Tuple

import sentry_sdk
from botocore.exceptions import ClientError

from common.config import config, models
from common.config.models import ModelAdapter
from common.config.tenant_config import TenantConfig
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.account_indexers.aws_organizations import retrieve_org_structure
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.tenant_integrations.aws import _handle_tenant_cache_tasks
from common.models import HubAccount, OrgAccount, SpokeAccount

log = config.get_logger(__name__)


def get_organizations_client(
    tenant: str, account_id: str, assume_role: str, read_only: bool = True
):
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
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
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


def _get_accounts_from_org(
    org_struc,
    org_id: Optional[str] = None,
    accounts: Optional[list] = None,
):
    if accounts is None:
        accounts = list()
        for _, org_dict in org_struc.items():
            if isinstance(org_dict, str):
                continue
            if org_id and org_id not in org_dict["Arn"]:
                continue
            _get_accounts_from_org(org_dict, org_id, accounts)

    if org_struc.get("Type") == "ACCOUNT":
        accounts.append(org_struc)

    for child in org_struc.get("Children", []):
        _get_accounts_from_org(child, org_id, accounts)

    return accounts


def _get_accounts(
    child_accounts: list[dict],
    current_accounts_excluded: list[str],
    last_update: Optional[str],
    force: bool,
) -> list[str]:
    """Get accounts from org when they are expired"""
    if not last_update:
        return []

    last_update_dt = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")

    # if expire or force, force the update
    if force or (last_update_dt + timedelta(hours=1) < datetime.utcnow()):
        return []

    expired_accounts = []
    for account_id in current_accounts_excluded or []:
        if account_id in list(map(lambda acc: acc.get("Id"), child_accounts)):
            expired_accounts.append(account_id)
    return expired_accounts


async def onboard_new_accounts_from_orgs(tenant: str, force: bool = False) -> list[str]:
    log_data = {"function": "onboard_new_accounts_from_orgs", "tenant": tenant}
    new_accounts_onboarded = []
    new_accounts_excluded = []
    org_accounts: list[OrgAccount] = (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    )  # type: ignore
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    org_struc = await get_org_structure(tenant)
    external_id = config.get_tenant_specific_key("tenant_details.external_id", tenant)
    hub_account = (
        models.ModelAdapter(HubAccount).load_config("hub_account", tenant).model
    )

    db_tenant = TenantConfig.get_instance(tenant)

    for org_account in org_accounts:
        if not force and (
            not org_account.automatically_onboard_accounts or not org_account.role_names
        ):
            continue
        try:
            child_accounts = _get_accounts_from_org(org_struc, org_account.org_id)
            spoke_role_name: str = db_tenant.get_spoke_role(org_account.account_id)

            hub_sts_client = boto3_cached_conn(
                "sts",
                tenant,
                None,
                region=config.region,
                session_name="noq_onboard_new_accounts_from_hub_acc",
            )

            current_excluded_accounts = _get_accounts(
                child_accounts,
                org_account.accounts_excluded_from_automatic_onboard or [],
                org_account.last_updated_accounts_excluded_automatic_onboard,
                force,
            )

            if current_excluded_accounts:
                new_accounts_excluded = (
                    new_accounts_excluded + current_excluded_accounts
                )

            for aws_account in child_accounts:
                account_id = aws_account.get("Id")
                log_data["account_id"] = account_id

                if spoke_accounts.query({"account_id": account_id}):
                    log.debug({"message": "Account already in Noq", **log_data})
                    continue  # We already know about this account, and can skip it

                if account_id in current_excluded_accounts:
                    log.debug(
                        {
                            "message": "Automatic onboarding disabled for this account",
                            **log_data,
                        }
                    )
                    continue

                try:
                    # If hub account can assume role in spoke account
                    # it means that spoke account is already onboarded
                    spoke_role_arn = f"arn:aws:iam::{account_id}:role/{spoke_role_name}"

                    await aio_wrapper(
                        hub_sts_client.assume_role,
                        RoleArn=spoke_role_arn,
                        RoleSessionName="noq_onboard_new_accounts_from_hub_acc",
                    )

                except ClientError as err:
                    log.error(
                        "Account can't be onboarded",
                        code=err.response.get("Error").get("Code"),
                        account=account_id,
                    )
                    new_accounts_excluded.append(aws_account)
                    continue

                # Save new SpokeAccount
                spoke_account = SpokeAccount(
                    name=spoke_role_name,
                    account_name=aws_account.get("Name"),
                    account_id=account_id,
                    role_arn=spoke_role_arn,
                    external_id=external_id,
                    hub_account_arn=hub_account.role_arn,
                    read_only=True,
                    org_management_account=False,
                    org_access_checked=False,
                    owners=[],
                    viewers=[],
                    delegate_admin_to_owner=False,
                    restrict_viewers_of_account_resources=False,
                )

                await models.ModelAdapter(
                    SpokeAccount, "handle_central_account_registration"
                ).load_config("spoke_accounts", tenant).from_model(
                    spoke_account
                ).store_item_in_list()

                new_accounts_onboarded.append(spoke_account)
        except Exception as e:
            log.error(
                {
                    "error": f"Unable to retrieve roles from AWS Organizations: {e}",
                    **log_data,
                },
                exc_info=True,
            )
            sentry_sdk.capture_exception()

        if new_accounts_excluded:
            # Update the org account with the new accounts excluded from onboard
            org_account.accounts_excluded_from_automatic_onboard = list(
                set(
                    [
                        nac if isinstance(nac, str) else nac.get("Id")
                        for nac in new_accounts_excluded
                    ]
                )
            )
            org_account.last_updated_accounts_excluded_automatic_onboard = (
                datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            )

            await ModelAdapter(
                OrgAccount, "accounts_excluded_from_automatic_onboard"
            ).load_config("org_accounts", tenant).from_model(
                org_account
            ).with_object_key(
                ["org_id"]
            ).store_item_in_list()

    if new_accounts_onboarded:
        # Update the tenant cache for the new accounts
        from common.celery_tasks.celery_tasks import app as celery_app

        _handle_tenant_cache_tasks(
            celery_app,
            tenant,
            [acc.account_id for acc in new_accounts_onboarded],
            skip_cache_organization_structure=True,
        )

    return new_accounts_onboarded


async def sync_account_names_from_orgs(tenant: str) -> dict[str, str]:
    log_data = {"function": "sync_account_names_from_orgs", "tenant": tenant}
    org_account_id_to_name = {}
    account_names_synced = {}
    accounts_d: Dict[str, str] = await get_account_id_to_name_mapping(tenant)
    org_accounts = (
        ModelAdapter(OrgAccount, "sync_account_names_from_orgs_org_accounts")
        .load_config("org_accounts", tenant)
        .models
    )
    spoke_accounts = ModelAdapter(
        SpokeAccount, "sync_account_names_from_orgs_spoke_accounts"
    ).load_config("spoke_accounts", tenant)
    for org_account in org_accounts:
        if not org_account.sync_account_names:
            continue

        org_account_id = org_account.account_id

        try:
            spoke_account = spoke_accounts.with_query(
                {"account_id": org_account_id}
            ).first
        except ValueError:
            continue

        org_client = get_organizations_client(
            tenant, org_account_id, spoke_account.name
        )
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
            spoke_account_to_replace = spoke_accounts.with_query(
                {"account_id": account_id}
            ).first
            if (
                spoke_account_to_replace.account_name
                == org_account_id_to_name[account_id]
            ):
                continue
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
        # Handle Access Denied Exception
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDeniedException":
                log.debug(
                    "Unable to retrieve organization details due to AccessDeniedException",
                    account_id=account_id,
                    tenant=tenant,
                )
            else:
                log.exception(
                    "Unable to retrieve organization details for account",
                    account_id=account_id,
                    tenant=tenant,
                )
        except Exception:
            log.exception(
                "Unable to retrieve roles from AWS Organizations",
                account_id=account_id,
                tenant=tenant,
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
                    "uuid": str(uuid.uuid4()),  # This is a new org account
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
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
    }
    all_org_structure = {}
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant)
    for organization in (
        ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    ):
        org_uuid = organization.uuid
        org_account_id = organization.account_id
        try:
            role_to_assume = spoke_accounts.with_query(
                {"account_id": org_account_id}
            ).first.name
        except ValueError:
            role_to_assume = None
        if not org_account_id:
            raise MissingConfigurationValue(
                "Your AWS Organizations Management Account ID is not specified in configuration. "
                "Unable to sync accounts from "
                "AWS Organizations"
            )

        if not role_to_assume:
            raise MissingConfigurationValue(
                "Noq doesn't know what role to assume to retrieve account information "
                "from AWS Organizations. please set the appropriate configuration value."
            )
        try:
            org_structure = await retrieve_org_structure(
                org_account_id,
                tenant,
                role_to_assume=role_to_assume,
                region=config.region,
            )
            org_structure["uuid"] = str(org_uuid)
            all_org_structure.update(org_structure)
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error(
                {
                    **log_data,
                    "message": "Unable to retrieve roles from AWS Organizations",
                    "error": str(e),
                    "org_uuid": org_uuid,
                    "org_account_id": org_account_id,
                    "role_to_assume": role_to_assume,
                    "region": config.region,
                },
                exc_info=True,
            )
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
