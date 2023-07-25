import uuid

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.iambic.config.models import TrustedProvider
from common.pg_core.models import Base
from common.request_types.models import (
    change_type_iambic_template_provider_definition_association,
    iambic_template_provider_defs_express_access_request_association,
)
from common.tenants.models import Tenant  # noqa: F401


class IambicTemplate(Base):
    __tablename__ = "iambic_template"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    repo_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    template_type = Column(String, nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)

    tenant = relationship("Tenant")
    content = relationship(
        "IambicTemplateContent",
        back_populates="iambic_template",
        cascade="all, delete-orphan",
        uselist=False,
    )
    provider_definition_refs = relationship(
        "IambicTemplateProviderDefinition",
        back_populates="iambic_template",
        cascade="all, delete-orphan",
        uselist=True,
    )
    express_access_requests = relationship(
        "ExpressAccessRequest",
        back_populates="iambic_template",
        cascade="all, delete-orphan",
        uselist=True,
    )

    __table_args__ = (
        Index(
            "iambic_tmplt_tp_template_type_idx",
            "tenant_id",
            "provider",
            "template_type",
        ),
        Index(
            "iambic_tmplt_tt_w_resource_id_idx",
            "tenant_id",
            "template_type",
            "resource_id",
        ),
        Index("iambic_tmplt_tp_resource_idx", "tenant_id", "provider", "resource_type"),
        Index(
            "iambic_tmplt_tp_resource_w_id_idx",
            "tenant_id",
            "provider",
            "resource_type",
            "resource_id",
        ),
        Index(
            "iambic_tmplt_tenant_repo_file_idx", "tenant_id", "repo_name", "file_path"
        ),
        Index(
            "uix_iambic_tmplt_idx",
            "tenant_id",
            "provider",
            "resource_type",
            "resource_id",
            "template_type",
            "repo_name",
            unique=True,
        ),
    )

    def dict(self):
        response = {
            "id": str(self.id),
            "template_type": str(self.template_type),
            "provider": str(self.provider),
            "resource_type": str(self.resource_type),
        }
        return response


class IambicTemplateContent(Base):
    # DO NOT put this in the IambicTemplate table, the content is unbound in size
    __tablename__ = "iambic_template_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    iambic_template_id = Column(UUID, ForeignKey("iambic_template.id"))
    content = Column(JSON)

    tenant = relationship("Tenant")
    iambic_template = relationship("IambicTemplate", back_populates="content")

    __table_args__ = (
        Index(
            "uix_tenant_template_content_idx",
            "tenant_id",
            "iambic_template_id",
            unique=True,
        ),
    )


class IambicTemplateProviderDefinition(Base):
    __tablename__ = "iambic_template_provider_definition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    iambic_template_id = Column(UUID, ForeignKey("iambic_template.id"), nullable=False)
    resource_id = Column(String, nullable=False)
    secondary_resource_id = Column(String, nullable=True)
    tenant_provider_definition_id = Column(
        UUID, ForeignKey("tenant_provider_definition.id"), nullable=False
    )
    tenant = relationship("Tenant")
    iambic_template = relationship(
        "IambicTemplate", back_populates="provider_definition_refs"
    )
    tenant_provider_definition = relationship("TenantProviderDefinition")

    associated_change_types = relationship(
        "ChangeType",
        secondary=change_type_iambic_template_provider_definition_association,
        back_populates="included_iambic_template_provider_definition",
        uselist=True,
    )
    associated_express_access_requests = relationship(
        "ExpressAccessRequest",
        secondary=iambic_template_provider_defs_express_access_request_association,
        back_populates="iambic_template_provider_defs",
    )

    __table_args__ = (
        Index("itpd_template_id_idx", "iambic_template_id"),
        Index("itpd_template_resource_id_idx", "iambic_template_id", "resource_id"),
        Index("itpd_tenant_resource_idx", "tenant_id", "resource_id"),
        Index(
            "itpd_tenant_secondary_resource_idx", "tenant_id", "secondary_resource_id"
        ),
        Index("itpd_provider_def_idx", "tenant_provider_definition_id"),
        Index(
            "itpd_template_and_provider_def_uix",
            "iambic_template_id",
            "tenant_provider_definition_id",
            unique=True,
        ),
    )

    def dict(self):
        response = {
            "id": str(self.id),
            "iambic_template_id": str(self.iambic_template_id),
            "resource_id": str(self.resource_id),
        }
        return response


# At some point we should probably create an IambicTemplateProviderDefinitionContent table
# DO NOT put it in the IambicTemplateProviderDefinition table, the content is unbound in size
