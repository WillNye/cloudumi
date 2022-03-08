from typing import List, Optional

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import HubAccount, OrgAccount, SpokeAccount

hub_account_key_name = "hub_account"
spoke_account_key_name = "spoke_accounts"
org_account_key_name = "org_accounts"
updated_by_name = "noq_automated_account_management"


async def delete_hub_account(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if hub_account_key_name not in host_config:
        return False
    del host_config[hub_account_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )
    return True


async def get_hub_account(host: str) -> Optional[HubAccount]:
    hub_account_config = config.get_host_specific_key(hub_account_key_name, host, {})
    if not hub_account_config:
        return None
    hub_account = HubAccount(**hub_account_config)
    return hub_account


async def set_hub_account(host: str, hub_account: HubAccount):
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    host_config[hub_account_key_name] = dict(hub_account)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


def __get_unique_spoke_account_key_name(name: str, account_id: str) -> str:
    return f"{name}__{account_id}"


def __get_unique_spoke_account_key_path(name: str, account_id: str) -> str:
    return ".".join(
        [spoke_account_key_name, __get_unique_spoke_account_key_name(name, account_id)]
    )


async def upsert_spoke_account(host: str, spoke_account: SpokeAccount):
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    spoke_key_name = __get_unique_spoke_account_key_name(
        spoke_account.name, spoke_account.account_id
    )
    if spoke_account_key_name not in host_config:
        host_config[spoke_account_key_name] = dict()
    host_config[spoke_account_key_name][spoke_key_name] = dict(spoke_account)
    if not host_config.get("account_ids_to_name"):
        host_config["account_ids_to_name"] = {}
    host_config["account_ids_to_name"][
        spoke_account.account_id
    ] = spoke_account.account_id

    if not host_config.get("policies", {}):
        host_config["policies"] = {}

    if not host_config.get("policies", {}).get("role_name"):
        host_config["policies"]["role_name"] = spoke_account.name

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_spoke_account(host: str, name: str, account_id: str) -> bool:
    ddb = RestrictedDynamoHandler()
    spoke_key_path = __get_unique_spoke_account_key_path(name, account_id)
    spoke_account_config = config.get_host_specific_key(spoke_key_path, host, {})
    if not spoke_account_config:
        return False
    host_config = config.get_tenant_static_config_from_dynamo(host)
    try:
        del host_config[spoke_account_key_name][
            __get_unique_spoke_account_key_name(name, account_id)
        ]
    except KeyError:
        return False

    if host_config.get("account_ids_to_name", {}).get(account_id):
        del host_config["account_ids_to_name"][account_id]

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )

    return True


async def delete_spoke_accounts(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if spoke_account_key_name not in host_config:
        return False
    try:
        del host_config[spoke_account_key_name]
    except KeyError:
        return False
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def get_spoke_accounts(host: str) -> List[SpokeAccount]:
    spoke_accounts = config.get_host_specific_key(spoke_account_key_name, host)
    if not spoke_accounts:
        return []
    return [SpokeAccount(**x) for x in spoke_accounts.values()]


def __get_unique_org_account_key_name(org_id: str) -> str:
    return org_id


def __get_unique_org_account_key_path(org_id: str) -> str:
    return ".".join([org_account_key_name, __get_unique_org_account_key_name(org_id)])


async def upsert_org_account(host: str, org_account: OrgAccount):
    ddb = RestrictedDynamoHandler()
    org_key_name = __get_unique_org_account_key_name(org_account.org_id)
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if org_account_key_name not in host_config:
        host_config[org_account_key_name] = dict()
    host_config[org_account_key_name][org_key_name] = dict(org_account)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_org_account(host: str, org_id: str) -> bool:
    ddb = RestrictedDynamoHandler()
    org_key_path = __get_unique_org_account_key_path(org_id)
    org_account_config = config.get_host_specific_key(org_key_path, host)
    if not org_account_config:
        return False
    host_config = config.get_tenant_static_config_from_dynamo(host)
    try:
        del host_config[org_account_key_name][__get_unique_org_account_key_name(org_id)]
    except KeyError:
        return False
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def delete_org_accounts(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if org_account_key_name not in host_config:
        return False
    try:
        del host_config[org_account_key_name]
    except KeyError:
        return False
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def get_org_accounts(host: str) -> List[OrgAccount]:
    org_accounts = config.get_host_specific_key(org_account_key_name, host)
    if not org_accounts:
        return []
    return [OrgAccount(**x) for x in org_accounts.values()]
