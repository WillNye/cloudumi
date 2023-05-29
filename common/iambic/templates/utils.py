from sqlalchemy import select

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.models import IambicTemplate


async def list_tenant_templates(
    tenant_id: int,
    template_type: str = None,
    resource_id: str = None,
    page_size: int = None,
    page: int = 1,
) -> list[IambicTemplate]:
    if resource_id:
        assert (
            template_type
        ), "template_type query param must be provided if resource_id is provided"

    async with ASYNC_PG_SESSION() as session:
        stmt = select(IambicTemplate).filter(
            IambicTemplate.tenant_id == tenant_id
        )  # noqa: E712
        if template_type:
            stmt = stmt.filter(
                IambicTemplate.template_type == template_type
            )  # noqa: E712
        if resource_id:
            stmt = stmt.filter(
                IambicTemplate.resource_id.ilike(f"%{resource_id}%")
            )  # noqa: E712

        if template_type:
            stmt = stmt.order_by(IambicTemplate.resource_id)
        else:
            stmt = stmt.order_by(
                IambicTemplate.resource_type, IambicTemplate.resource_id
            )

        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)

    return items.scalars().all()
