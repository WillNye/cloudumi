import enum
import uuid
from datetime import datetime
from typing import Optional, Union

from asyncache import cached
from cachetools import TTLCache
from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    and_,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import relationship

from common.config.globals import ASYNC_PG_SESSION
from common.exceptions.exceptions import NoMatchingRequest
from common.groups.models import Group
from common.identity.models import AwsIdentityRole
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant
from common.users.models import User


class RoleAccessTypes(enum.Enum):
    credential_access = 1
    tra_supported_group = 2
    tra_active_user = 3


class AWSRoleAccess(SoftDeleteMixin, Base):
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
        "User", lazy="joined", primaryjoin="User.id == AWSRoleAccess.user_id"
    )
    group = relationship(
        "Group", lazy="joined", primaryjoin="Group.id == AWSRoleAccess.group_id"
    )
    identity_role = relationship(
        "AwsIdentityRole",
        lazy="joined",
        primaryjoin="AwsIdentityRole.id == AWSRoleAccess.identity_role_id",
    )
    tenant = relationship(
        "Tenant", primaryjoin="Tenant.id == AWSRoleAccess.tenant_id"
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
            type=self.type.value,
            user=self.user.dict() if self.user else {},
            group=self.group.dict() if self.group else {},
            identity_role=self.identity_role.dict() if self.identity_role else {},
            cli_only=self.cli_only,
            expiration=str(self.expiration),
            request_id=self.request_id,
            cloud_provider=self.cloud_provider,
            signature=self.signature,
        )

    @classmethod
    @cached(cache=TTLCache(maxsize=1024, ttl=30))
    async def get_roles_by_user_email(cls, email):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                # Get the user by email
                user_stmt = select(User).where(User.email == email)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar()

                # Get the groups of the user
                groups_stmt = select(Group).where(Group.users.contains(user))
                groups_result = await session.execute(groups_stmt)
                groups = groups_result.scalars().all()

                # Get the AWSRoleAccess instances related to the user and their groups
                aws_role_access_stmt = select(AWSRoleAccess).where(
                    or_(
                        AWSRoleAccess.user_id == user.id,
                        AWSRoleAccess.group_id.in_([group.id for group in groups]),
                    )
                )
                aws_role_access_result = await session.execute(aws_role_access_stmt)
                aws_role_accesses = aws_role_access_result.scalars().all()

                # Return the role names from the AWSRoleAccess instances
                return [
                    aws_role_access.role_name for aws_role_access in aws_role_accesses
                ]

    @classmethod
    async def create(
        cls,
        tenant: Tenant,
        type: RoleAccessTypes,
        identity_role: AwsIdentityRole,
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
    async def bulk_create(cls, tenant: Tenant, role_access_data: list[dict]):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                for role_access in role_access_data:
                    insert_stmt_data = {
                        "tenant_id": tenant.id,
                        "type": role_access["type"],
                        "identity_role_id": role_access["identity_role"].id,
                        "cli_only": role_access["cli_only"],
                        "expiration": role_access["expiration"],
                    }
                    if "user" in role_access.keys():
                        insert_stmt_data["user_id"] = role_access["user"].id
                    elif "group" in role_access.keys():
                        insert_stmt_data["group_id"] = role_access["group"].id
                    upsert_stmt_data = insert_stmt_data.copy()
                    insert_stmt = insert(cls).values(insert_stmt_data)
                    if role_access.get("user"):
                        insert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=["tenant_id", "user_id", "identity_role_id"],
                            set_=upsert_stmt_data,
                        )
                    elif role_access.get("group"):
                        insert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=[
                                "tenant_id",
                                "group_id",
                                "identity_role_id",
                            ],
                            set_=upsert_stmt_data,
                        )
                    else:
                        raise ValueError("Must provide either user or group")
                    await session.execute(insert_stmt)

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                await session.delete(self)
                await session.commit()
        return True

    # @classmethod
    # async def delete(cls, tenant, role_access_id):
    #     async with ASYNC_PG_SESSION() as session:
    #         async with session.begin():
    #             await session.execute(
    #                 delete(AWSRoleAccess).where(
    #                     and_(
    #                         AWSRoleAccess.id == role_access_id, AWSRoleAccess.tenant == tenant
    #                     )
    #                 )
    #             )

    @classmethod
    async def get_by_user_and_role_arn(cls, tenant: Tenant, user: User, role_arn: str):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                identity_role = await AwsIdentityRole.get_by_role_arn(tenant, role_arn)
                stmt = select(AWSRoleAccess).where(
                    and_(
                        AWSRoleAccess.tenant == tenant,
                        AWSRoleAccess.user == user,
                        AWSRoleAccess.identity_role == identity_role,
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
                        select(AWSRoleAccess)
                        .filter(AWSRoleAccess.id == role_access_id)
                        .filter(AWSRoleAccess.tenant == tenant)
                    )
                else:
                    raise NoMatchingRequest

                items = await session.execute(stmt)
                request: AWSRoleAccess = items.scalars().unique().one()
                return request
        except Exception:
            raise NoMatchingRequest

    @classmethod
    async def get_by_arn(cls, tenant, role_arn):
        try:
            async with ASYNC_PG_SESSION() as session:
                identity_role = await AwsIdentityRole.get_by_role_arn(tenant, role_arn)
                if role_arn:
                    stmt = (
                        select(AWSRoleAccess)
                        .filter(AWSRoleAccess.identity_role == identity_role)
                        .filter(AWSRoleAccess.tenant == tenant)
                    )
                else:
                    raise NoMatchingRequest

                items = await session.execute(stmt)
                request: AWSRoleAccess = items.scalars().unique().one()
                return request
        except Exception:
            raise NoMatchingRequest

    @classmethod
    async def get_by_attr(cls, attribute, value):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(AWSRoleAccess).filter(
                getattr(AWSRoleAccess, attribute) == value
            )
            items = await session.execute(stmt)
            return items.scalars().first()

    @classmethod
    async def list(cls, tenant):
        async with ASYNC_PG_SESSION() as session:
            stmt = select(AWSRoleAccess).filter(AWSRoleAccess.tenant == tenant)

            # stmt = create_filter_from_url_params(stmt, **filter_kwargs)
            items = await session.execute(stmt)
        return items.scalars().all()

    @classmethod
    async def list_by_user(cls, tenant: Tenant, user: User):
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                select(AWSRoleAccess)
                .filter(AWSRoleAccess.tenant == tenant)
                .filter(AWSRoleAccess.user == user)
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
        identity_role: Optional[AwsIdentityRole],
    ):
        async with ASYNC_PG_SESSION() as session:
            select_stmt = select(AWSRoleAccess).filter(AWSRoleAccess.tenant == tenant)
            if user:
                select_stmt = select_stmt.filter(AWSRoleAccess.user == user)
            if group:
                select_stmt = select_stmt.filter(AWSRoleAccess.group == group)
            if identity_role:
                select_stmt = select_stmt.filter(
                    AWSRoleAccess.identity_role == identity_role
                )
            items = await session.execute(select_stmt)
            role_access: AWSRoleAccess = items.scalars().unique().all()
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
        identity_role: Optional[AwsIdentityRole] = None,
        cli_only: Optional[bool] = None,
        expiration: Optional[datetime] = None,
        request_id: Optional[str] = None,
        cloud_provider: Optional[str] = "aws",
        signature: Optional[str] = None,
    ):
        arguments = locals()
        role_access = await AWSRoleAccess.get_by_id(tenant, role_access_id)
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
                    update(AWSRoleAccess)
                    .where(AWSRoleAccess.id == role_access_id)
                    .values(*updates)
                )
