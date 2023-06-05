from typing import Optional

from sqlalchemy import select

from common.config.globals import ASYNC_PG_SESSION
from common.groups.models import Group


async def list_tenant_groups(
    tenant_id: int,
    name: Optional[str] = None,
    exclude_deleted: Optional[bool] = True,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
) -> list[Group]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(Group).filter(Group.tenant_id == tenant_id)
        if name:
            stmt = stmt.filter(Group.name.ilike(f"%{name}%"))
        if exclude_deleted:
            stmt = stmt.filter(Group.deleted == False)
        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)

    return items.scalars().unique().all()
