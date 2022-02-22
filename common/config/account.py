from doctest import master

from asgiref.sync import sync_to_async

from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

hub_account_key_name = "hub_account"
spoke_account_key_name = "spoke_accounts"
org_account_key_name = "org_accounts"
updated_by_name = "noq_automated_account_management"


def __get_hub_account_mapping(
    name: str, account_id: str, role_arn: str, external_id: str
) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_arn": role_arn,
        "external_id": external_id,
    }


async def delete_hub_account(host: str) -> bool:
    deleted = False
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)
    if hub_account_key_name in host_config:
        del host_config[hub_account_key_name]
        deleted = True
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host
        )
    return deleted


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
        host_config = dict()
    host_config[hub_account_key_name] = __get_hub_account_mapping(
        name, account_id, role_name, external_id
    )

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


def __get_spoke_account_mapping(
    name: str,
    account_id: str,
    role_arn: str,
    external_id: str,
    hub_account_arn: str,
    master_for_account: bool = False,
) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_arn": role_arn,
        "external_id": external_id,
        "hub_account_arn": hub_account_arn,
        "master_for_account": master_for_account,
    }


def __get_unique_spoke_account_key_name(name: str, account_id: str) -> str:
    return f"{name}__{account_id}"


async def upsert_spoke_account(
    host: str,
    name: str,
    account_id: str,
    role_arn: str,
    external_id: str,
    hub_account_arn: str,
    master_for_account: bool = False,
):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    if not host_config.get(spoke_account_key_name):
        host_config[spoke_account_key_name] = dict()
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    host_config[spoke_account_key_name][spoke_key_name] = __get_spoke_account_mapping(
        name, account_id, role_arn, external_id, hub_account_arn, master_for_account
    )

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_spoke_account(host: str, name: str, account_id: str) -> bool:
    deleted = False
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    if (
        spoke_account_key_name in host_config
        and spoke_key_name in host_config[spoke_account_key_name]
    ):
        del host_config[spoke_account_key_name][spoke_key_name]
        deleted = True

        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host  # type: ignore
        )

    return deleted


async def delete_spoke_accounts(host: str) -> bool:
    deleted = False
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    if spoke_account_key_name in host_config:
        del host_config[spoke_account_key_name]
        deleted = True
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host  # type: ignore
        )
    return deleted


async def get_spoke_accounts(host: str) -> list:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    spoke_accounts = [x for x in host_config.get(spoke_account_key_name, {}).values()]
    return spoke_accounts


def __get_org_account_mapping(
    org_id: str, account_id: str, account_name: str, owner: str
) -> dict:
    return {
        "org_id": org_id,
        "account_id": account_id,
        "account_name": account_name,
        "owner": owner,
    }


def __get_unique_org_account_key_name(org_id: str) -> str:
    return org_id


async def upsert_org_account(
    host: str,
    org_id: str,
    account_id: str,
    account_name: str,
    owner: str,
):
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    if not host_config.get(org_account_key_name):
        host_config[org_account_key_name] = dict()
    org_key_name = __get_unique_org_account_key_name(org_id)
    host_config[org_account_key_name][org_key_name] = __get_org_account_mapping(
        org_id, account_id, account_name, owner
    )

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_org_account(host: str, org_id: str) -> bool:
    deleted = False
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    org_key_name = __get_unique_org_account_key_name(org_id)
    if (
        org_account_key_name in host_config
        and org_key_name in host_config[org_account_key_name]
    ):
        del host_config[org_account_key_name][org_key_name]
        deleted = True
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host  # type: ignore
        )
    return deleted


async def delete_org_accounts(host: str) -> bool:
    deleted = False
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = dict()
    if org_account_key_name in host_config:
        del host_config[org_account_key_name]
        deleted = True
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host  # type: ignore
        )
    return deleted


async def get_org_accounts(host: str) -> list:
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    org_accounts = [x for x in host_config.get(org_account_key_name, {}).values()]
    return org_accounts
