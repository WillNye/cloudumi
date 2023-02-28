from common.config import config
from common.config.globals import IAMBIC_REPOS_BASE_KEY
from common.iambic_request.models import GitHubPullRequest, IambicTemplateChange
from common.models import IambicRepoDetails


async def get_allowed_approvers(
    tenant: str, request_pr, changes: list[IambicTemplateChange]
) -> list[str]:
    """Retrieve the list of allowed approvers from the template body.

    Not using template_bodies for now but may be used to resolve approvers in the future.
    The idea being that
    """
    return config.get_tenant_specific_key("groups.can_admin", tenant)


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


async def get_iambic_pr_instance(
    tenant: str, request_id: str, requested_by: str, pull_request_id: int = None
):
    iambic_repo: IambicRepoDetails = await get_iambic_repo(tenant)

    if iambic_repo.git_provider == "github":
        return GitHubPullRequest(
            tenant=tenant,
            request_id=str(request_id),
            requested_by=requested_by,
            pull_request_id=pull_request_id,
            repo_name=iambic_repo.repo_name,
            access_token=iambic_repo.access_token,
            merge_on_approval=iambic_repo.merge_on_approval,
        )

    raise ValueError(f"Unsupported git provider: {iambic_repo.git_provider}")
