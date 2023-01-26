from sqlalchemy import Column, Integer, String, and_
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin


class Tenant(SoftDeleteMixin, Base):
    __tablename__ = "tenant"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    organization_id = Column(String)

    @classmethod
    async def get_by_name(cls, tenant_name):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Tenant).where(
                    and_(
                        Tenant.name == tenant_name,
                        Tenant.deleted == False,  # noqa
                    )
                )
                tenant = await session.execute(stmt)
                return tenant.scalars().first()
