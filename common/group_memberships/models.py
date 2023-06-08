import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin
from common.pg_core.utils import bulk_add

if TYPE_CHECKING:
    from common.groups.models import Group
    from common.users.models import User


class GroupMembership(SoftDeleteMixin, Base):
    __tablename__ = "group_memberships"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    group_id = Column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )

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
    async def create(cls, user, group):
        if await GroupMembership.get(user, group):
            # Group membership already exists. No big deal.
            return False
        # Make sure there are no duplicates
        membership = cls(id=str(uuid.uuid4()), user_id=user.id, group_id=group.id)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(membership)
                await session.commit()
        return membership

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(self)
                await session.commit()
        return True


async def upsert_group_memberships(users: list[User], groups: list[Group]):
    """Upsert group memberships for a list of users and groups.
    Args:
        users (list[User]): List of users to upsert group memberships for.
        groups (list[Group]): List of groups to upsert group memberships for.
    Returns:
        bool: True if successful, False otherwise.
    """
    memberships = []
    for user in users:
        for group in groups:
            memberships.append(GroupMembership(user_id=user.id, group_id=group.id))
    if memberships:
        return await bulk_add(memberships)
    return memberships
