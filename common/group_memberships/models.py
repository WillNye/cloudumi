import uuid

from sqlalchemy import Column, ForeignKey, String, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="groups")
    group = relationship("Group", back_populates="users")

    @classmethod
    async def get(cls, user, group):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(GroupMembership).where(
                    and_(GroupMembership.user == user, GroupMembership.group == group)
                )
                membership = await session.execute(stmt)
                return membership.scalars().first()

    @classmethod
    async def create(cls, user, group):
        if await GroupMembership.get(user, group):
            # Group membership already exists. No big deal.
            return False
        # Make sure there are no duplicates
        membership = cls(id=str(uuid.uuid4()), user=user, group=group)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(membership)
                await session.commit()
        return membership

    @classmethod
    async def delete(cls, membership):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(membership)
                await session.commit()
        return membership


# User.group_memberships = relationship('GroupMembership', back_populates='user', cascade='all, delete-orphan')
# Group.group_memberships = relationship('GroupMembership', back_populates='group', cascade='all, delete-orphan')
