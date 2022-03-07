from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"


async def set_ip_restriction(host: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if "ip_restrictions" not in host_config:
        host_config["ip_restrictions"] = list()
    if ip_restriction in host_config["ip_restrictions"]:
        return False
    else:
        host_config["ip_restrictions"].append(ip_restriction)
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host
        )
    return True


async def get_ip_restrictions(host: str) -> list:
    return config.get_host_specific_key("ip_restrictions", host)


async def delete_ip_restriction(host: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if "ip_restrictions" not in host_config:
        return False
    if ip_restriction not in host_config["ip_restrictions"]:
        return False
    host_config["ip_restrictions"].pop(ip_restriction)
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )
    return True
