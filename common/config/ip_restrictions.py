import ipaddress

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"


async def set_ip_restriction(host: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    try:
        # Noteworthy: this will throw an exception if bits are set in the host field
        _ = ipaddress.ip_network(ip_restriction)
    except ValueError:
        return False
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if "aws" not in host_config:
        host_config["aws"] = dict()
    if "ip_restrictions" not in host_config["aws"]:
        host_config["aws"]["ip_restrictions"] = list()
    if ip_restriction in host_config["aws"]["ip_restrictions"]:
        return False
    else:
        host_config["aws"]["ip_restrictions"].append(ip_restriction)
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), updated_by_name, host
        )
    return True


async def get_ip_restrictions(host: str) -> list:
    ip_restrictions = config.get_host_specific_key("aws.ip_restrictions", host, [])
    return ip_restrictions


async def delete_ip_restriction(host: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if ip_restriction not in host_config.get("aws", {}).get("ip_restrictions", []):
        return False
    try:
        idx = host_config["aws"]["ip_restrictions"].index(ip_restriction)
    except ValueError:
        return False
    host_config["aws"]["ip_restrictions"].pop(idx)
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )
    return True


async def toggle_ip_restrictions(host: str, enabled: bool = False) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if "policies" not in host_config:
        host_config["policies"] = dict()
    if "ip_restrictions" not in host_config["policies"]:
        return False
    host_config["policies"]["ip_restrictions"] = enabled
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host
    )
    return True
