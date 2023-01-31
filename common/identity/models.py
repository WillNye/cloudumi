from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import relationship
from sqlalchemy.sql import delete, select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base
from common.tenants.models import Tenant


class IdentityRole(Base):
    __tablename__ = "identity_role"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    role_name = Column(String)
    role_arn = Column(String, index=True)

    tenant = relationship("Tenant", primaryjoin="Tenant.id == IdentityRole.tenant_id")

    __table_args__ = (
        UniqueConstraint("tenant_id", "role_arn", name="uq_tenant_role_arn"),
    )

    @classmethod
    async def create(
        cls,
        tenant: Tenant,
        role_name: str,
        role_arn: str,
    ):
        # Massage data
        upsert_stmt_data = {
            "tenant_id": tenant.id,
            "role_name": role_name,
            "role_arn": role_arn,
        }
        insert_stmt_data = upsert_stmt_data.copy()

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                insert_stmt = insert(cls).values(insert_stmt_data)
                insert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["tenant_id", "role_arn"],
                    set_=upsert_stmt_data,
                )
                await session.execute(insert_stmt)

    @classmethod
    async def delete(cls, tenant: Tenant, role_id: int):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.execute(
                    delete(IdentityRole).where(
                        and_(IdentityRole.id == role_id, IdentityRole.tenant == tenant)
                    )
                )

    @classmethod
    async def get_all(cls, tenant: Tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                    )
                )
                roles = await session.execute(stmt)
                return roles.scalars().all()

    @classmethod
    async def get_by_id(cls, tenant: Tenant, role_id: int):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                        IdentityRole.id == role_id,
                    )
                )
                user = await session.execute(stmt)
                return user.scalars().all()

    @classmethod
    async def get_by_role_arn(cls, tenant: Tenant, role_arn: str):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                        IdentityRole.role_arn == role_arn,
                    )
                )
                user = await session.execute(stmt)
                return user.scalars().first()
