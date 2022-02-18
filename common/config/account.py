from collections import defaultdict

from asgiref.sync import sync_to_async

from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

hub_account_key_name = "hub_account"
spoke_account_key_name = "hub_account"
updated_by_name = "noq_automated_account_management"


def __get_hub_account_mapping(
    name: str, account_id: str, role_name: str, external_id: str
) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_name": role_name,
        "external_id": external_id,
    }


async def delete_hub_account(host: str):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)
    del host_config[hub_account_key_name]
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )


async def get_hub_account(host: str) -> dict:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    hub_account = host_config.get(hub_account_key_name, {})
    return hub_account


async def set_hub_account(
    host: str, name: str, account_id: str, role_name: str, external_id: str
):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    host_config[hub_account_key_name] = __get_hub_account_mapping(
        name, account_id, role_name, external_id
    )

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


def __get_spoke_account_mapping(
    name: str, account_id: str, role_name: str, external_id: str, hub_account_name: str
) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_name": role_name,
        "external_id": external_id,
        "hub_account_name": hub_account_name,
    }


def __get_unique_spoke_account_key_name(name: str, account_id: str) -> str:
    return f"{name}:{account_id}"


async def upsert_spoke_account(
    host: str,
    name: str,
    account_id: str,
    role_name: str,
    external_id: str,
    hub_account_name: str,
):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    if not host_config.get(spoke_account_key_name):
        host_config[spoke_account_key_name] = defaultdict(dict)
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    host_config[spoke_account_key_name][spoke_key_name] = __get_spoke_account_mapping(
        name, account_id, role_name, external_id, hub_account_name
    )

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_spoke_account(host: str, name: str, account_id: str):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    if (
        spoke_account_key_name in host_config
        and spoke_key_name in host_config[spoke_account_key_name]
    ):
        del host_config[spoke_account_key_name][spoke_key_name]

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_spoke_accounts(host: str):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    if spoke_account_key_name in host_config:
        del host_config[spoke_account_key_name]

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def get_spoke_accounts(host: str) -> list:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    spoke_accounts = [x for x in host_config.get(spoke_account_key_name, {}).values()]
    return spoke_accounts
