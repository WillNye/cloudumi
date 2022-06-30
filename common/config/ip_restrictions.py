import ipaddress

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"


async def set_ip_restriction(tenant: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    try:
        # Noteworthy: this will throw an exception if bits are set in the tenant field
        _ = ipaddress.ip_network(ip_restriction)
    except ValueError:
        return False
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if "aws" not in tenant_config:
        tenant_config["aws"] = dict()
    if "ip_restrictions" not in tenant_config["aws"]:
        tenant_config["aws"]["ip_restrictions"] = list()
    if ip_restriction in tenant_config["aws"]["ip_restrictions"]:
        return False
    else:
        tenant_config["aws"]["ip_restrictions"].append(ip_restriction)
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), updated_by_name, tenant
        )
    return True


async def get_ip_restrictions(tenant: str) -> list:
    ip_restrictions = config.get_tenant_specific_key("aws.ip_restrictions", tenant, [])
    return ip_restrictions


async def delete_ip_restriction(tenant: str, ip_restriction: str) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if ip_restriction not in tenant_config.get("aws", {}).get("ip_restrictions", []):
        return False
    try:
        idx = tenant_config["aws"]["ip_restrictions"].index(ip_restriction)
    except ValueError:
        return False
    tenant_config["aws"]["ip_restrictions"].pop(idx)
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant
    )
    return True


async def toggle_ip_restrictions(tenant: str, enabled: bool = False) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    tenant_config.setdefault("policies", dict())
    tenant_config["policies"]["ip_restrictions"] = enabled
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant
    )
    return True


async def get_ip_restrictions_toggle(tenant: str) -> bool:
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    return tenant_config.get("policies", {}).get("ip_restrictions", False)


async def toggle_ip_restrictions_on_requester_ip_only(
    tenant: str, enabled: bool = False
) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    tenant_config.setdefault("policies", dict())
    tenant_config["policies"]["ip_restrictions_on_requesters_ip"] = enabled
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant
    )
    return True


async def get_ip_restrictions_on_requester_ip_only_toggle(tenant: str) -> bool:
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    return tenant_config.get("policies", {}).get(
        "ip_restrictions_on_requesters_ip", False
    )
