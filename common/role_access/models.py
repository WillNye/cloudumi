import enum
import uuid
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import relationship
from sqlalchemy.sql import delete, select, update
from sqlalchemy.types import Enum

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest
from common.groups.models import Group
from common.identity.models import IdentityRole
from common.pg_core.models import Base
from common.tenants.models import Tenant
from common.users.models import User


class RoleAccessTypes(enum.Enum):
    credential_access = 1
    tra_supported_group = 2
    tra_active_user = 3


class RoleAccess(Base):
    __tablename__ = "role_access"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer(), ForeignKey("tenant.id"))
    type = Column(Enum(RoleAccessTypes))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"))
    identity_role_id = Column(
        Integer(), ForeignKey("identity_role.id", ondelete="CASCADE")
    )
    cli_only = Column(Boolean, default=False)
    expiration = Column(DateTime, nullable=True)
    request_id = Column(String)
    cloud_provider = Column(String, default="aws")
    signature = Column(String, nullable=True)

    user = relationship(
        "User", lazy="joined", primaryjoin="User.id == RoleAccess.user_id"
    )
    group = relationship(
        "Group", lazy="joined", primaryjoin="Group.id == RoleAccess.group_id"
    )
    identity_role = relationship(
        "IdentityRole",
        lazy="joined",
        primaryjoin="IdentityRole.id == RoleAccess.identity_role_id",
    )
    tenant = relationship(
        "Tenant", primaryjoin="Tenant.id == RoleAccess.tenant_id"
    )  # do not need to resolve tenant

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", "identity_role_id", name="uq_tenant_user_role"
        ),
        UniqueConstraint(
            "tenant_id", "group_id", "identity_role_id", name="uq_tenant_group_role"
        ),
    )

    def dict(self):
        return dict(
            id=self.id,
            tenant_id=self.tenant_id,
            type=self.type.value,
            user=self.user.dict() if self.user else {},
            group=self.group.dict() if self.group else {},
            identity_role=self.identity_role.dict() if self.identity_role else {},
            cli_only=self.cli_only,
            expiration=self.expiration,
            request_id=self.request_id,
            cloud_provider=self.cloud_provider,
            signature=self.signature,
        )

    @classmethod
    async def create(
        cls,
        tenant: Tenant,
        type: RoleAccessTypes,
        identity_role: IdentityRole,
        cli_only: bool,
        expiration: datetime,
        group: Group = None,
        user: User = None,
    ):
        insert_stmt_data = {
            "tenant_id": tenant.id,
            "type": type,
            "identity_role_id": identity_role.id,
            "cli_only": cli_only,
            "expiration": expiration,
        }
        if user:
            insert_stmt_data["user_id"] = user.id
        elif group:
            insert_stmt_data["group_id"] = group.id
        else:
            raise ValueError("Must provide either a user or group")
        upsert_stmt_data = insert_stmt_data.copy()
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                insert_stmt = insert(cls).values(insert_stmt_data)
                if user:
                    insert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["tenant_id", "user_id", "identity_role_id"],
                        set_=upsert_stmt_data,
                    )
                elif group:
                    insert_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=["tenant_id", "group_id", "identity_role_id"],
                        set_=upsert_stmt_data,
                    )
                else:
                    raise ValueError("Must provide either user or group")
                await session.execute(insert_stmt)

    @classmethod
    async def delete(cls, tenant, role_access_id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.execute(
                    delete(RoleAccess).where(
                        and_(
                            RoleAccess.id == role_access_id, RoleAccess.tenant == tenant
                        )
                    )
                )

    @classmethod
    async def get_by_user_and_role_arn(
        cls, tenant_name: str, user: User, role_arn: str
    ):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                tenant = await Tenant.get_by_name(tenant_name)
                identity_role = await IdentityRole.get_by_role_arn(
                    tenant_name, role_arn
                )
                stmt = select(RoleAccess).where(
                    and_(
                        RoleAccess.tenant == tenant,
                        RoleAccess.user == user,
                        RoleAccess.identity_role == identity_role,
                    )
                )
                role_access = await session.execute(stmt)
                return role_access.scalars().first()

    @classmethod
    async def get_by_id(cls, tenant, role_access_id):
        try:
            async with ASYNC_PG_SESSION() as session:
                if role_access_id:
                    stmt = (
                        select(RoleAccess)
                        .filter(RoleAccess.id == role_access_id)
                        .filter(RoleAccess.tenant == tenant)
                    )
                else:
                    raise NoMatchingRequest

                items = await session.execute(stmt)
                request: RoleAccess = items.scalars().unique().one()
                return request
        except Exception:
            raise NoMatchingRequest

    @classmethod
    async def get_by_arn(cls, tenant, role_arn):
        try:
            async with ASYNC_PG_SESSION() as session:
                identity_role = await IdentityRole.get_by_role_arn(role_arn)
                if role_arn:
                    stmt = (
                        select(RoleAccess)
                        .filter(RoleAccess.identity_role == identity_role)
                        .filter(RoleAccess.tenant == tenant)
                    )
                else:
                    raise NoMatchingRequest

                items = await session.execute(stmt)
                request: RoleAccess = items.scalars().unique().one()
                return request
        except Exception:
            raise NoMatchingRequest

    @classmethod
    async def get_by_attr(cls, attribute, value):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(RoleAccess).filter(getattr(RoleAccess, attribute) == value)
            items = await session.execute(stmt)
            return items.scalars().first()

    @classmethod
    async def list(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(RoleAccess).filter(RoleAccess.tenant == tenant)

            # stmt = create_filter_from_url_params(stmt, **filter_kwargs)
            items = await session.execute(stmt)
        return items.scalars().all()

    @classmethod
    async def list_by_user(cls, tenant: Tenant, user: User):
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(RoleAccess)
                .filter(RoleAccess.tenant == tenant)
                .filter(RoleAccess.user == user)
            )

            # stmt = create_filter_from_url_params(stmt, **filter_kwargs)
            items = await session.execute(stmt)
        return items.scalars().all()

    @classmethod
    async def query(
        cls,
        tenant: Tenant,
        user: Optional[User],
        group: Optional[Group],
        identity_role: Optional[IdentityRole],
    ):
        async with ASYNC_PG_SESSION() as session:
            select_stmt = select(RoleAccess).filter(RoleAccess.tenant == tenant)
            if user:
                select_stmt = select_stmt.filter(RoleAccess.user == user)
            if group:
                select_stmt = select_stmt.filter(RoleAccess.group == group)
            if identity_role:
                select_stmt = select_stmt.filter(
                    RoleAccess.identity_role == identity_role
                )
            items = await session.execute(select_stmt)
            role_access: RoleAccess = items.scalars().unique().all()
            return role_access

    @classmethod
    async def update(
        cls,
        tenant: str,
        role_access_id: Union[str, uuid.UUID],
        updated_by: str,
        type: Optional[RoleAccessTypes] = None,
        user: Optional[User] = None,
        group: Optional[Group] = None,
        identity_role: Optional[IdentityRole] = None,
        cli_only: Optional[bool] = None,
        expiration: Optional[datetime] = None,
        request_id: Optional[str] = None,
        cloud_provider: Optional[str] = "aws",
        signature: Optional[str] = None,
    ):
        arguments = locals()
        role_access = await RoleAccess.get_by_id(tenant, role_access_id)
        if (
            updated_by not in role_access.allowed_approvers
        ) or role_access.status != "Pending":
            raise RuntimeError("Unable to update this role_access")

        updates = [
            arg
            for arg in arguments
            if arg and arg != "role_access_id" and arg != "tenant"
        ]

        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.execute(
                    update(RoleAccess)
                    .where(RoleAccess.id == role_access_id)
                    .values(*updates)
                )
