import uuid
from uuid import uuid4

from sqlalchemy import Column, String, UniqueConstraint, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership
from common.pg_core.models import Base, SoftDeleteMixin


class Group(SoftDeleteMixin, Base):
    __tablename__ = "groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    description = Column(String)
    tenant = Column(String, nullable=False)
    email = Column(String)
    __table_args__ = (
        UniqueConstraint("tenant", "name", name="uq_tenant_name"),
        UniqueConstraint("tenant", "email", name="uq_group_tenant_email"),
    )

    users = relationship("GroupMembership", back_populates="group", lazy="subquery")

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True

    @classmethod
    async def get_by_name(cls, tenant, name):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(
                        Group.tenant == tenant,
                        Group.name == name,
                        Group.deleted is False,
                    ),
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

    async def delete(self):
        # Delete all group memeberships
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                group_memberships = await session.execute(
                    select(GroupMembership).where(
                        and_(
                            GroupMembership.group_id == self.id,
                        )
                    )
                )
                for group_membership in group_memberships:
                    await group_membership.delete()
                self.deleted = True
                self.name = f"{self.name}-{self.id}"
                self.email = f"{self.email}-{self.id}"
                await self.write()

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
                stmt = select(Group).where(
                    Group.tenant == tenant, Group.deleted is False
                )
                groups = await session.execute(stmt)
                return groups.scalars().all()
