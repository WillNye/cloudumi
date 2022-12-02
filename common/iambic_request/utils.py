from common.config import models
from common.models import IambicRepoDetails

IAMBIC_REPOS_BASE_KEY = "iambic_repos"


async def save_iambic_repos(tenant: str, iambic_repos: list[IambicRepoDetails]):
    await models.ModelAdapter(IambicRepoDetails, "save_iambic_repos").load_config(
        IAMBIC_REPOS_BASE_KEY, tenant
    ).from_model(iambic_repos).store_list()


async def get_iambic_repo(tenant: str) -> IambicRepoDetails:
    """Retrieve the proper IAMbic repo.
    Currently, we really only support one repo per tenant.
    """
    iambic_repos: list[IambicRepoDetails] = (
        models.ModelAdapter(IambicRepoDetails)
        .load_config(IAMBIC_REPOS_BASE_KEY, tenant)
        .models
    )
    return iambic_repos[0]
