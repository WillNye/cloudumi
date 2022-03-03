from typing import List, Optional

from asgiref.sync import sync_to_async

from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import HubAccount, OrgAccount, SpokeAccount

hub_account_key_name = "hub_account"
spoke_account_key_name = "spoke_accounts"
org_account_key_name = "org_accounts"
updated_by_name = "noq_automated_account_management"


async def delete_hub_account(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)
    if hub_account_key_name not in host_config:
        return False
    del host_config[hub_account_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )
    return True


async def get_hub_account(host: str) -> Optional[HubAccount]:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    hub_account_config = host_config.get(hub_account_key_name, {})
    if not hub_account_config:
        return None
    hub_account = HubAccount(**host_config.get(hub_account_key_name, {}))
    return hub_account


async def set_hub_account(host: str, hub_account: HubAccount):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    host_config[hub_account_key_name] = dict(hub_account)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


def __get_unique_spoke_account_key_name(name: str, account_id: str) -> str:
    return f"{name}__{account_id}"


async def upsert_spoke_account(host: str, spoke_account: SpokeAccount):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    if not host_config.get(spoke_account_key_name):
        host_config[spoke_account_key_name] = dict()
    spoke_key_name = __get_unique_spoke_account_key_name(
        spoke_account.name, spoke_account.account_id
    )
    host_config[spoke_account_key_name][spoke_key_name] = dict(spoke_account)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_spoke_account(host: str, name: str, account_id: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    if not host_config.get(spoke_account_key_name, {}).get(spoke_key_name):
        return False
    del host_config[spoke_account_key_name][spoke_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )

    return True


async def delete_spoke_accounts(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    if spoke_account_key_name not in host_config:
        return False
    del host_config[spoke_account_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def get_spoke_accounts(host: str) -> List[SpokeAccount]:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    spoke_accounts = [
        SpokeAccount(**x) for x in host_config.get(spoke_account_key_name, {}).values()
    ]
    return spoke_accounts


def __get_unique_org_account_key_name(org_id: str) -> str:
    return org_id


async def upsert_org_account(host: str, org_account: OrgAccount):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    if not host_config.get(org_account_key_name):
        host_config[org_account_key_name] = dict()
    org_key_name = __get_unique_org_account_key_name(org_account.org_id)
    host_config[org_account_key_name][org_key_name] = dict(org_account)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_org_account(host: str, org_id: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    org_key_name = __get_unique_org_account_key_name(org_id)
    if not host_config.get(org_account_key_name, {}).get(org_key_name):
        return False
    del host_config[org_account_key_name][org_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def delete_org_accounts(host: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        raise RuntimeError("No host config! This is bad - something went really wrong")
    if org_account_key_name not in host_config:
        return False
    del host_config[org_account_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def get_org_accounts(host: str) -> List[OrgAccount]:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    org_accounts = [
        OrgAccount(**x) for x in host_config.get(org_account_key_name, {}).values()
    ]
    return org_accounts
