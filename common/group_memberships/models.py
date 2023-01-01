import uuid

from sqlalchemy import Column, ForeignKey, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="groups")
    group = relationship("Group", back_populates="users")

    @classmethod
    async def get(cls, user, group):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(GroupMembership).where(
                    and_(
                        GroupMembership.user_id == user.id,
                        GroupMembership.group_id == group.id,
                    )
                )
                membership = await session.execute(stmt)
                return membership.scalars().first()

    @classmethod
    async def get_groups_by_user(cls, user):
        # Get group memberships for a user
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(GroupMembership)
                    .where(GroupMembership.user_id == user.id)
                    .options(selectinload(GroupMembership.group))
                )
                memberships = await session.execute(stmt)
                groups = [
                    membership.group for membership in memberships.scalars().all()
                ]
                return groups

    @classmethod
    async def get_users_by_group(cls, group):
        # Get group memberships for a user
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(GroupMembership)
                    .where(GroupMembership.group_id == group.id)
                    .options(selectinload(GroupMembership.user))
                )
                memberships = await session.execute(stmt)
                users = [membership.user for membership in memberships.scalars().all()]
                return users

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
        return True


# User.group_memberships = relationship('GroupMembership', back_populates='user', cascade='all, delete-orphan')
# Group.group_memberships = relationship('GroupMembership', back_populates='group', cascade='all, delete-orphan')
