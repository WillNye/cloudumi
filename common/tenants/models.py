from sqlalchemy import Column, DateTime, Integer, String, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin


class Tenant(SoftDeleteMixin, Base):
    __tablename__ = "tenant"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    organization_id = Column(String)
    groups = relationship(
        "Group", back_populates="tenant", cascade="all, delete-orphan"
    )
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    iambic_templates_last_parsed = Column(DateTime, nullable=True)

    @classmethod
    async def get_by_id(cls, tenant_id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Tenant).where(
                    and_(
                        Tenant.id == tenant_id,
                        Tenant.deleted == False,  # noqa
                    )
                )
                tenant = await session.execute(stmt)
                return tenant.scalars().first()

    def dict(self):
        return dict(
            id=self.id,
            name=self.name,
            organization_id=self.organization_id,
        )

    @classmethod
    async def create(cls, **kwargs):
        tenant = cls(**kwargs)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(tenant)
                await session.commit()
        return tenant

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(self)
                await session.commit()
        return True

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True

    @classmethod
    async def get_by_name(cls, tenant_name, session=None):
        async def _query(session):
            stmt = select(Tenant).where(
                and_(
                    Tenant.name == tenant_name,
                    Tenant.deleted == False,  # noqa
                )
            )
            tenant = await session.execute(stmt)
            return tenant.scalars().first()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)

    @classmethod
    async def get_all(cls, session=None):
        async def _query(session):
            stmt = select(Tenant).where(
                and_(
                    Tenant.deleted == False,  # noqa
                )
            )
            tenants = await session.execute(stmt)
            return tenants.scalars().all()

        if session:
            return await _query(session)

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                return await _query(session)

    @classmethod
    async def get_by_attr(cls, attribute, value):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(Tenant).filter(getattr(Tenant, attribute) == value)
            items = await session.execute(stmt)
            return items.scalars().first()
