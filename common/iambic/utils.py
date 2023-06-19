from typing import Optional

from common.config import config
from common.config.globals import IAMBIC_REPOS_BASE_KEY
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import IambicRepoDetails


async def save_iambic_repos(
    tenant_name: str, iambic_repos: IambicRepoDetails, user: str
) -> bool:

    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant_name)
    if not tenant_config:
        raise KeyError(f"No tenant config found for {tenant_name}")

    tenant_config["iambic_repos"] = [iambic_repos.dict()]

    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), user, tenant_name
    )
    return True


async def delete_iambic_repos(tenant_name: str, user: str):
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant_name)
    if not tenant_config:
        raise KeyError(f"No tenant config found for {tenant_name}")

    tenant_config["iambic_repos"] = []

    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), user, tenant_name
    )
    return True


async def get_iambic_repo(tenant_name: str) -> Optional[IambicRepoDetails]:
    """Retrieve the proper IAMbic repo.
    Currently, we really only support one repo per tenant.
    """
    from common.config import models

    iambic_repos: list[IambicRepoDetails] = (
        models.ModelAdapter(IambicRepoDetails)
        .load_config(IAMBIC_REPOS_BASE_KEY, tenant_name)
        .models
    )
    if not iambic_repos:
        return None

    return iambic_repos[0]
