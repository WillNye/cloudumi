import uuid
from typing import Optional, Union

from sqlalchemy import Column, ForeignKey, Integer, String, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.groups.models import Group
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant


class IdentityRole(SoftDeleteMixin, Base):
    __tablename__ = "identity_role"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    role_name = Column(String)
    role_arn = Column(String, index=True)

    tenant = relationship("Tenant", primaryjoin="Tenant.id == IdentityRole.tenant_id")

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

    @classmethod
    async def create(cls, tenant: Tenant, role_name: str, role_arn: str):
        identity_role = cls(tenant=tenant, role_name=role_name, role_arn=role_arn)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(identity_role)
                await session.commit()
        return identity_role
