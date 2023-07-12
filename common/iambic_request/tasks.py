from datetime import datetime
from typing import Optional

from sqlalchemy import select

from common.config.config import get_logger
from common.config.globals import ASYNC_PG_SESSION
from common.iambic_request.models import Request
from common.iambic_request.utils import get_iambic_pr_instance
from common.tenants.models import Tenant

log = get_logger(__name__)


async def handle_tenant_iambic_github_event(
    tenant_id: int,
    repo_name: str,
    pull_request: int,
    pr_created_at: datetime,
    approved_by: Optional[list[str]],
    is_closed: Optional[bool],
    is_merged: Optional[bool],
):
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(Request)
            .filter(Request.repo_name == repo_name)
            .filter(Request.pull_request_id == pull_request)
            .filter(Request.tenant_id == tenant_id)
        )

        items = await session.execute(stmt)
        request: Request = items.scalars().unique().one_or_none()

    if not request:
        # TODO: Support creating a new request when a PR is created outside of the SaaS app
        return

    tenant = await Tenant.get_by_id(tenant_id)
    request_pr = await get_iambic_pr_instance(
        tenant, request.id, request.created_by, request.pull_request_id
    )
    await request_pr.load_pr()

    if approved_by and not is_closed and not is_merged:
        if request_pr.merge_on_approval:
            await request_pr.merge_request(request.approved_by)
        else:
            request.status = "Pending in Git"
    elif is_merged:
        request.status = "Applied"
        approved_by = [approver for approver in approved_by if "[bot]" not in approver]
        request.approved_by = list(set(request.approved_by + approved_by))
        await request_pr.remove_branch(pull_default=True)
    elif is_closed:
        request.status = "Rejected"
        await request_pr.remove_branch(pull_default=True)
    else:
        log.warning(
            {
                "message": "Received a Git callback event that could not be handled.",
                "tenant_id": tenant_id,
                "repo_name": repo_name,
                "pull_request": pull_request,
                "is_closed": is_closed,
                "is_merged": is_merged,
            }
        )

    request.updated_at = datetime.utcnow()
    await request.write()
