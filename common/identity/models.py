from sqlalchemy import and_, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select
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

    async def get_by_role_arn(self, tenant_name: str, role_arn: str):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                tenant = await Tenant.get_by_name(tenant_name)
                stmt = select(IdentityRole).where(
                    and_(
                        IdentityRole.tenant == tenant,
                        IdentityRole.role_arn == role_arn,
                        IdentityRole.deleted == False,  # noqa
                    )
                )
                user = await session.execute(stmt)
                return user.scalars().first()
