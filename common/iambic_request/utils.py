from common.config import config
from common.iambic.utils import get_iambic_repo
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
