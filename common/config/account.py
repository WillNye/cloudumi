from asgiref.sync import sync_to_async
from collections import defaultdict
from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"

def __get_hub_account_mapping(name: str, account_id: str, role_name: str, external_id: str) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_name": role_name,
        "external_id": external_id,
    }

async def set_hub_account(host: str, name: str, account_id: str, role_name: str, external_id: str):
    ddb = RestrictedDynamoHandler()
    hub_account_key_name = "hub_account"
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    host_config[hub_account_key_name] = __get_hub_account_mapping(name, account_id, role_name, external_id)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


def __get_spoke_account_mapping(name: str, account_id: str, role_name: str, external_id: str, hub_account_name: str) -> dict:
    return {
        "name": name,
        "account_id": account_id,
        "role_name": role_name,
        "external_id": external_id,    
        "hub_account_name": hub_account_name,
    }


def __get_unique_spoke_account_key_name(name: str, account_id: str) -> str:
    return f"{name}:{account_id}"


async def add_spoke_account(host: str, name: str, account_id: str, role_name: str, external_id: str, hub_account_name: str):
    ddb = RestrictedDynamoHandler()
    spoke_account_key_name = "hub_account"
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)  # type: ignore
    if not host_config:
        host_config = defaultdict(dict)
    if not host_config.get(spoke_account_key_name):
        host_config[spoke_account_key_name] = defaultdict(dict)
    spoke_key_name = __get_unique_spoke_account_key_name(name, account_id)
    host_config[spoke_account_key_name][spoke_key_name] = \
        __get_spoke_account_mapping(name, account_id, role_name, external_id, hub_account_name)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
