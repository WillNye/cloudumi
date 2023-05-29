from common.config.globals import IAMBIC_REPOS_BASE_KEY
from common.models import IambicRepoDetails


async def save_iambic_repos(tenant: str, iambic_repos: list[IambicRepoDetails]):
    from common.config import models

    await models.ModelAdapter(IambicRepoDetails, "save_iambic_repos").load_config(
        IAMBIC_REPOS_BASE_KEY, tenant
    ).from_model(iambic_repos).store_list()


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
