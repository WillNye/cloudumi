from common.config import config
from common.config.globals import IAMBIC_REPOS_BASE_KEY
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import IambicRepoDetails


async def save_iambic_repos(
    tenant: str, iambic_repos: list[IambicRepoDetails], user: str
) -> bool:

    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if not tenant_config:
        raise KeyError(f"No tenant config found for {tenant}")

    tenant_config["iambic_repos"] = [iambic_repos.dict()]

    await ddb.update_static_config_for_tenant(yaml.dump(tenant_config), user, tenant)
    return True


async def get_iambic_repo(tenant: str) -> IambicRepoDetails:
    """Retrieve the proper IAMbic repo.
    Currently, we really only support one repo per tenant.
    """
    from common.config import models

    iambic_repos: list[IambicRepoDetails] = (
        models.ModelAdapter(IambicRepoDetails)
        .load_config(IAMBIC_REPOS_BASE_KEY, tenant)
        .models
    )
    if not iambic_repos:
        raise KeyError(f"No IAMbic repos configured for {tenant}")

    return iambic_repos[0]
