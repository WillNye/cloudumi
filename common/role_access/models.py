import enum
import uuid
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select, update
from sqlalchemy.types import Enum

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest
from common.groups.models import Group
from common.identity.models import IdentityRole
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant
from common.users.models import User


class RoleAccessTypes(enum.Enum):
    credential_access = 1
    tra_supported_group = 2
    tra_active_user = 3


class RoleAccess(SoftDeleteMixin, Base):
    __tablename__ = "role_access"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer(), ForeignKey("tenant.id"))
    type = Column(Enum(RoleAccessTypes))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"))
    identity_role_id = Column(Integer(), ForeignKey("identity_role.id"))
    cli_only = Column(Boolean, default=False)
    expiration = Column(DateTime, nullable=True)
    request_id = Column(String)
    cloud_provider = Column(String, default="aws")
    signature = Column(String, nullable=True)

    user = relationship("User")
    group = relationship("Group", primaryjoin="Group.id == RoleAccess.group_id")
    identity_role = relationship(
        "IdentityRole", primaryjoin="IdentityRole.id == RoleAccess.identity_role_id"
    )
    tenant = relationship("Tenant", primaryjoin="Tenant.id == RoleAccess.tenant_id")

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
                        RoleAccess.deleted == False,  # noqa
                    )
                )
                role_access = await session.execute(stmt)
                return role_access.scalars().first()

    def dict(self):
        return dict(
            id=self.id,
            tenant_id=self.tenant_id,
            type=self.type.value,
            user_id=self.user_id,
            group_id=self.group_id,
            identity_role_id=self.identity_role_id,
            cli_only=self.cli_only,
            expiration=self.expiration,
            request_id=self.request_id,
            cloud_provider=self.cloud_provider,
            signature=self.signature,
            created_by=self.created_by,
            created_at=self.created_at,
        )

    @classmethod
    async def create(cls, tenant, type, identity_role, cli_only, expiration, created_by, group=None, user=None):
        role_access = RoleAccess(
            tenant=tenant,
            type=type,
            user=user,
            group=group,
            identity_role=identity_role,
            cli_only=cli_only,
            expiration=expiration,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(role_access)

    @classmethod
    async def delete(cls, tenant, role_access_id):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.execute(
                    update(RoleAccess)
                    .where(RoleAccess.id == role_access_id)
                    .where(RoleAccess.tenant == tenant)
                    .values(deleted=True, deleted_at=datetime.utcnow())
                )

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
            (
                role_access.created_by != updated_by
                and updated_by not in role_access.allowed_approvers
            )
            or role_access.status != "Pending"
            or role_access.deleted
        ):
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
