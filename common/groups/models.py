import uuid
from uuid import uuid4

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, UniqueConstraint, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql import select

from common.config.globals import ASYNC_PG_SESSION
from common.group_memberships.models import GroupMembership
from common.pg_core.filters import (
    DEFAULT_SIZE,
    create_filter_from_url_params,
    determine_page_from_offset,
)
from common.pg_core.models import Base, SoftDeleteMixin
from common.pg_core.utils import bulk_add
from common.tenants.models import Tenant  # noqa: F401


class Group(SoftDeleteMixin, Base):
    __tablename__ = "groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    managed_by = Column(
        Enum("MANUAL", "SCIM", "SSO", name="managed_by_enum"), nullable=True
    )
    name = Column(String, index=True)
    description = Column(String)
    tenant_id = Column(Integer(), ForeignKey("tenant.id"))
    email = Column(String)
    tenant = relationship("Tenant", order_by=name)
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_name"),
        UniqueConstraint("tenant_id", "email", name="uq_group_tenant_email"),
    )

    users = relationship(
        "User",
        secondary=GroupMembership.__table__,
        back_populates="groups",
        lazy="joined",
        foreign_keys=[GroupMembership.user_id, GroupMembership.group_id],
    )

    def dict(self):
        return dict(
            id=str(self.id),
            name=self.name,
            description=self.description,
            managed_by=self.managed_by,
            email=self.email,
            users=[user.email for user in self.users],
        )

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True

    @classmethod
    async def get_by_id(cls, tenant, id, get_users=False):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(
                        Group.tenant == tenant,
                        Group.id == id,
                        Group.deleted == False,  # noqa
                    ),
                )
                if get_users:
                    stmt = stmt.options(selectinload(Group.users))
                group = await session.execute(stmt)
                return group.scalars().first()

    @classmethod
    async def get_by_name(cls, tenant, name):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(
                        Group.tenant == tenant,
                        Group.name == name,
                        Group.deleted == False,  # noqa
                    ),
                )
                group = await session.execute(stmt)
                return group.scalars().first()

    @classmethod
    async def get_by_names(cls, tenant, names: list) -> list["Group"]:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(
                        Group.tenant == tenant,
                        Group.name.in_(names),
                        Group.deleted == False,  # noqa
                    ),
                )
                result = await session.scalars(stmt)
                return result.unique().all()

    @classmethod
    async def get_by_email(cls, tenant, email):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    and_(
                        Group.tenant == tenant,
                        Group.email == email,
                        Group.deleted == False,  # noqa
                    ),
                )
                group = await session.execute(stmt)
                return group.scalars().first()

    @classmethod
    async def get_by_attr(cls, attribute, value):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(Group).filter(getattr(Group, attribute) == value)
            items = await session.execute(stmt)
            return items.scalars().first()

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
                self.deleted = True
                self.name = f"{self.name}-{self.id}"
                self.email = f"{self.email}-{self.id}"
                await self.write()
        for group_membership in group_memberships.scalars().all():
            await group_membership.delete()

    async def update(self, group, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(group)
                await session.commit()
        return group

    @classmethod
    async def get_all(
        cls, tenant, get_users=False, count=DEFAULT_SIZE, offset=0, page=0, filters=None
    ):
        if not filters:
            filters = {}
        if not page:
            page = determine_page_from_offset(offset, count)
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = select(Group).where(
                    Group.tenant == tenant, Group.deleted == False  # noqa
                )
                stmt = create_filter_from_url_params(stmt, page, count, **filters)
                if get_users:
                    stmt = stmt.options(selectinload(Group.users))
                groups = await session.execute(stmt)
                return groups.unique().scalars().all()

    async def serialize_for_scim(self):
        users = []

        for user in self.users:
            users.append({"display": user.username, "value": user.id})

        return {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:Group",
            ],
            "id": self.id,
            "meta": {
                "resourceType": "Group",
            },
            "displayName": self.name,
            "members": users,
        }


async def upsert_groups_by_name(
    tenant: Tenant, group_names: list[str], description: str, managed_by: str, **kwargs
):
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = select(Group).where(
                and_(Group.tenant_id == tenant.id, Group.name.in_(group_names))
            )
            result = await session.execute(stmt)
            existing_groups = result.unique().scalars().all()

    existing_group_names = {group.name for group in existing_groups}

    # Create new groups that do not exist yet
    new_group_names = set(group_names) - existing_group_names
    new_groups = [
        Group(
            managed_by=managed_by,
            name=group,
            description=description,
            tenant_id=tenant.id,
            **kwargs,
        )
        for group in new_group_names
    ]
    if new_groups:
        await bulk_add(new_groups)

    return {
        "existing_groups": existing_groups,
        "new_groups": new_groups,
        "all_groups": existing_groups + new_groups,
    }
