from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import insert, select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant


class AWSAccount(SoftDeleteMixin, Base):
    __tablename__ = "aws_account"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String)
    number = Column(String, index=True)
    tenant_id = Column(ForeignKey("tenant.id"))

    tenant = relationship(
        "Tenant", order_by=number, primaryjoin="Tenant.id == AWSAccount.tenant_id"
    )

    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_tenant_number"),)

    @classmethod
    async def create(cls, tenant: Tenant, name: str, number: str, created_by: str):
        upsert_stmt_data = {
            "tenant_id": tenant.id,
            "name": name,
            "number": number,
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
                    index_elements=["tenant_id", "number"],
                    set_=upsert_stmt_data,
                )
                await session.execute(insert_stmt)

    @classmethod
    async def get_by_tenant(cls, tenant: Tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(AWSAccount).where(
                    and_(
                        AWSAccount.tenant == tenant,
                        AWSAccount.deleted == False,  # noqa
                    )
                )
                accounts = await session.execute(stmt)
                return accounts.scalars().all()
