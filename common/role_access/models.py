import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum

from common.pg_core.models import Base, SoftDeleteMixin


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
    group_id = (
        Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE")),
    )
    identity_role_id = Column(Integer(), ForeignKey("identity_role.id"))
    cli_only = Column(Boolean, default=False)
    expiration = Column(DateTime, nullable=True)
    request_id = Column(String)
    cloud_provider = Column(String, default="aws")
    signature = Column(String, nullable=True)

    user = relationship("User", back_populates="role_access", order_by=expiration)
    group = relationship("Group", back_populates="role_access", order_by=expiration)
    identity_role = relationship(
        "IdentityRole", back_populates="role_access", uselist=False
    )

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
