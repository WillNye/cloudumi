import uuid

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from common.config import config
from common.pg_core.models import Base
from common.tenants.models import Tenant

log = config.get_logger(__name__)

TrustedProvider = ENUM(
    "aws", "google_workspace", "okta", "azure_ad", name="ProviderEnum"
)


class TenantProvider(Base):
    __tablename__ = "tenant_provider"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    sub_type = Column(String, nullable=False, default="")

    tenant = relationship(Tenant)

    uix_tp_tenant_provider = UniqueConstraint("tenant_id", "provider", "sub_type")

    __table_args__ = (Index("tp_tenant_idx", "tenant_id"),)


class TenantProviderDefinition(Base):
    __tablename__ = "tenant_provider_definition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    sub_type = Column(String, nullable=True)
    name = Column(String, nullable=False)
    definition = Column(JSON, nullable=True)

    tenant = relationship(Tenant)

    uix_tenant_provider_name = UniqueConstraint(
        "tenant_id", "provider", "sub_type", "name"
    )

    __table_args__ = (
        Index("tpd_tenant_idx", "tenant_id"),
        Index("tpd_tenant_provider_idx", "tenant_id", "provider"),
    )
