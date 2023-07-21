import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, and_, column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import Values, select

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.models import Base, SoftDeleteMixin
from common.pg_core.utils import bulk_add, bulk_delete

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
    async def get_by_user(cls, user) -> list["GroupMembership"]:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(GroupMembership).where(
                    and_(
                        GroupMembership.user_id == user.id,
                    )
                )
                membership = await session.execute(stmt)
                return membership.scalars().all()

    @classmethod
    async def get_by_group(cls, group) -> list["GroupMembership"]:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(GroupMembership).where(
                    and_(
                        GroupMembership.group_id == group.id,
                    )
                )
                membership = await session.execute(stmt)
                return membership.scalars().all()

    @classmethod
    async def exists_by_group_and_user(cls, user, group) -> bool:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(GroupMembership)
                    .where(
                        and_(
                            GroupMembership.group_id == group.id,
                            GroupMembership.user_id == user.id,
                        )
                    )
                    .exists()
                )
                result = await session.scalars(select(True).filter(stmt))
                return result.unique().first() or False

    @classmethod
    async def get_by_user_and_group(cls, user, group) -> "GroupMembership":
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(GroupMembership).where(
                    and_(
                        GroupMembership.group_id == group.id,
                        GroupMembership.user_id == user.id,
                    )
                )
                result = await session.scalars(stmt)
                return result.unique().first()

    @classmethod
    async def exists_by_users_and_groups(
        cls, users_groups: list[tuple["User", "Group"]]
    ) -> "GroupMembership":
        # reference: https://github.com/sqlalchemy/sqlalchemy/blob/main/test/sql/test_values.py

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                cte = select(
                    Values(
                        column("user_id", UUID), column("group_id", UUID), name="data"
                    ).data(list(map(lambda ug: (ug[0].id, ug[1].id), users_groups)))
                ).cte("info")

                stmt = select(GroupMembership).join_from(
                    cte,
                    GroupMembership,
                    and_(
                        GroupMembership.user_id == cte.c.user_id,
                        GroupMembership.group_id == cte.c.group_id,
                    ),
                    isouter=True,
                )

                result = await session.execute(stmt)
                return result.scalars().all()

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


async def upsert_and_remove_group_memberships(
    users,
    groups,
    remove_other_group_memberships: bool = True,
):
    """Upsert group memberships for a list of users and groups.
    Args:
        users (list[User]): List of users to upsert group memberships for.
        groups (list[Group]): List of groups to upsert group memberships for.
    Returns:
        bool: True if successful, False otherwise.
    """
    memberships = []
    memberships_to_remove = []
    for user in users:
        if remove_other_group_memberships:
            existing_memberships = await GroupMembership.get_by_user(user)
            for membership in existing_memberships:
                if membership.group_id not in [group.id for group in groups]:
                    memberships_to_remove.append(membership)
        for group in groups:
            memberships.append(GroupMembership(user_id=user.id, group_id=group.id))
    if memberships_to_remove:
        await bulk_delete(memberships_to_remove)
    if memberships:
        return await bulk_add(memberships)
    return memberships
