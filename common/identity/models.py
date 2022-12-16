import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import Enum

from common.pg_core.models import Base, SoftDeleteMixin


class RoleAccessTypes(enum.Enum):
    credential_access = 1
    tra_supported_group = 2
    tra_active_user = 3


class RoleAccess(SoftDeleteMixin, Base):
    __tablename__ = "role_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant = Column(String)
    type = Column(Enum(RoleAccessTypes))
    user_id = Column(String)  # Might become a foreign key to user table
    group_id = Column(String)  # Might become a foreign key to group table
    role_arn = Column(String)
    cli_only = Column(Boolean, default=False)
    expiration = Column(DateTime, nullable=True)
    request_id = Column(String)
    cloud_provider = Column(String, default="aws")
    signature = Column(String, nullable=True)

    def dict(self):
        return dict(
            id=self.id,
            tenant=self.tenant,
            type=self.type.value,
            user_id=self.user_id,
            group_id=self.group_id,
            role_arn=self.role_arn,
            cli_only=self.cli_only,
            expiration=self.expiration,
            request_id=self.request_id,
            cloud_provider=self.cloud_provider,
            signature=self.signature,
            created_by=self.created_by,
            created_at=self.created_at,
        )
