import uuid

from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.iambic.config.models import TrustedProvider
from common.pg_core.models import Base
from common.tenants.models import Tenant  # noqa: F401


class IambicTemplate(Base):
    __tablename__ = "iambic_template"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
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
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    iambic_template_id = Column(UUID, ForeignKey("iambic_template.id"))
    tenant_provider_definition_id = Column(
        UUID, ForeignKey("tenant_provider_definition.id")
    )

    tenant = relationship("Tenant")
    iambic_template = relationship(
        "IambicTemplate", back_populates="provider_definition_refs"
    )
    tenant_provider_definition = relationship("TenantProviderDefinition")

    __table_args__ = (
        Index("itpd_template_id_idx", "iambic_template_id"),
        Index("itpd_provider_def_idx", "tenant_provider_definition_id"),
        Index(
            "itpd_template_and_provider_def_idx",
            "iambic_template_id",
            "tenant_provider_definition_id",
        ),
    )


# At some point we should probably create an IambicTemplateProviderDefinitionContent table
# DO NOT put it in the IambicTemplateProviderDefinition table, the content is unbound in size
