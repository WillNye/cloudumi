from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import insert, select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant


class IdentityRole(SoftDeleteMixin, Base):
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
        cls, tenant: Tenant, role_name: str, role_arn: str, created_by: str
    ):
        # Massage data
        upsert_stmt_data = {
            "tenant_id": tenant.id,
            "role_name": role_name,
            "role_arn": role_arn,
        }
        insert_stmt_data = upsert_stmt_data.copy()
        insert_stmt_data["created_by"] = created_by
        insert_stmt_data["created_at"] = datetime.utcnow()
        upsert_stmt_data["deleted"] = False
        upsert_stmt_data["deleted_at"] = None

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
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                        IdentityRole.id == role_id,
                        IdentityRole.deleted == False,  # noqa
                    )
                )
                role = await session.execute(stmt)
                role = role.scalars().first()
                role.deleted = True
                session.add(role)
                await session.commit()

    @classmethod
    async def get_all(cls, tenant: Tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                        IdentityRole.deleted == False,  # noqa
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
                        IdentityRole.deleted == False,  # noqa
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
                        IdentityRole.deleted == False,  # noqa
                    )
                )
                user = await session.execute(stmt)
                return user.scalars().first()
