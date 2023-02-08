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

    def dict(self):
        return dict(
            id=self.id,
            role_name=self.role_name,
            role_arn=self.role_arn,
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
    async def bulk_create(cls, tenant: Tenant, identity_role_data: list[dict]):
        # Massage data
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                for identity_role in identity_role_data:
                    role_name = identity_role["role_name"]
                    role_arn = identity_role["role_arn"]
                    upsert_stmt_data = {
                        "tenant_id": tenant.id,
                        "role_name": role_name,
                        "role_arn": role_arn,
                    }
                    insert_stmt_data = upsert_stmt_data.copy()
                    insert_stmt = insert(cls).values(insert_stmt_data)
                    insert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["tenant_id", "role_arn"],
                        set_=upsert_stmt_data,
                    )
                    await session.add(insert_stmt)
                await session.flush()

    @classmethod
    async def delete(cls, tenant: Tenant, role_ids: list[int]):
        if isinstance(role_ids, int):
            role_ids = [role_ids]
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.execute(
                    delete(IdentityRole).where(
                        and_(IdentityRole.id in role_ids, IdentityRole.tenant == tenant)
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

    @classmethod
    async def get_by_attr(cls, attribute, value):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(IdentityRole).filter(
                getattr(IdentityRole, attribute) == value
            )
            items = await session.execute(stmt)
            return items.scalars().first()
