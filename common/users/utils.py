from typing import Optional

from sqlalchemy import select

from common.config.globals import ASYNC_PG_SESSION
from common.users.models import User


async def list_tenant_users(
    tenant_id: int,
    email: Optional[str] = None,
    exclude_deleted: Optional[bool] = True,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
) -> list[User]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(User).filter(User.tenant_id == tenant_id)
        if email:
            stmt = stmt.filter(User.email.ilike(f"%{email}%"))
        if exclude_deleted:
            stmt = stmt.filter(User.deleted == False)
        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)

    return items.scalars().unique().all()
