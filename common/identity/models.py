import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import Enum

from common.users.models import User
from common.pg_core.models import Base, SoftDeleteMixin


class RoleAccessTypes(enum.Enum):
    credential_access = 1
    tra_supported_group = 2
    tra_active_user = 3


class Tenant(SoftDeleteMixin, Base):
    __tablename__ = "tenant"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    organization_id = Column(String)


class AWSAccount(SoftDeleteMixin, Base):
    __tablename__ = "aws_account"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String)
    number = Column(String, index=True)
    tenant_id = ForeignKey("tenant.id")

    tenant = relationship("Tenant", backref=backref("aws_account", order_by=number))

class IdentityRole(SoftDeleteMixin, Base):
    __tablename__ = "identity_role"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = ForeignKey("tenant.id")
    role_name = Column(String)
    role_arn = Column(String, index=True)

    tenant = relationship("Tenant", backref=backref("identity_role", order_by=role_name))


class RoleAccess(SoftDeleteMixin, Base):
    __tablename__ = "role_access"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(Integer(), ForeignKey("tenant.id"))
    type = Column(Enum(RoleAccessTypes))
    user_id = Column(Integer(), ForeignKey("users.id"))
    group_id = Column(Integer(), ForeignKey("groups.id"))  # Might become a foreign key to group table
    identity_role_id = Column(Integer(), ForeignKey("identity_role.id"))
    cli_only = Column(Boolean, default=False)
    expiration = Column(DateTime, nullable=True)
    request_id = Column(String)
    cloud_provider = Column(String, default="aws")
    signature = Column(String, nullable=True)

    user = relationship("User", backref=backref("role_access", order_by=expiration))
    group = relationship("Group", backref=backref("role_access", order_by=expiration))
    identity_role = relationship("IdentityRole", backref=backref("role_access", uselist=False))

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
