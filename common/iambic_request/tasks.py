from datetime import datetime
from typing import Optional

from sqlalchemy import select

from common.config.globals import ASYNC_PG_SESSION
from common.iambic_request.models import Request
from common.iambic_request.utils import get_iambic_pr_instance
from common.tenants.models import Tenant


async def handle_tenant_iambic_github_event(
    tenant_id: int,
    repo_name: str,
    pull_request: int,
    status: str,
    pr_created_at: datetime,
    approved_by: Optional[list[str]],
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

    if status == request.status or (
        status == "Pending" and request.status == "Running"
    ):
        return  # No change
    elif status == "Closed":
        request.status = "Approved" if is_merged else "Rejected"
        if is_merged:
            request.approved_by.extend(approved_by)

        tenant = await Tenant.get_by_id(tenant_id)
        request_pr = await get_iambic_pr_instance(
            tenant, request.id, request.created_by, request.pull_request_id
        )
        await request_pr.load_pr()
        await request_pr.remove_branch(pull_default=True)
    else:
        request.status = status

    request.updated_at = datetime.utcnow()
    await request.write()
