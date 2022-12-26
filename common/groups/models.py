from uuid import uuid4

from sqlalchemy import Column, String, UniqueConstraint, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base


class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(String)
    tenant = Column(String, nullable=False)
    email = Column(String)
    __table_args__ = (
        UniqueConstraint("tenant", "name", name="uq_tenant_name"),
        UniqueConstraint("tenant", "email", name="uq_group_tenant_email"),
    )

    users = relationship(
        "GroupMembership",
        back_populates="group",
    )

    # users = relationship(
    #     'User',
    #     secondary='group_memberships',
    #     back_populates='groups',
    # )

    @classmethod
    async def get_by_name(cls, tenant, name):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(Group.tenant == tenant, Group.name == name),
                )
                group = await session.execute(stmt)
                return group.scalars().first()

    @classmethod
    async def create(cls, **kwargs):
        group = cls(id=str(uuid4()), **kwargs)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(group)
                await session.commit()
        return group

    @classmethod
    async def delete(cls, group):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(group)
                await session.commit()
        return group

    async def update(self, group, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(group)
                await session.commit()
        return group

    @classmethod
    async def get_all(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(Group.tenant == tenant)
                groups = await session.execute(stmt)
                return groups.scalars().all()
