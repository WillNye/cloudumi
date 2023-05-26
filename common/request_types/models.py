import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, Integer, String, update
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID
from sqlalchemy.orm import relationship

from common.config import config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant  # noqa: F401

log = config.get_logger(__name__)

FieldType = ENUM(
    "TextBox",
    "TypeAhead",
    "EnforcedTypeAhead",
    "CheckBox",
    "Choice",
    "CallbackChoice",
    name="FieldTypeEnum",
)
ApplyAttrBehavior = ENUM("Append", "Merge", "Replace", name="ApplyAttrBehaviorEnum")
"""ApplyAttrBehavior describes how the value is added to the template.
Append:
    That means the resource value is a list that can be extended with the new value.
    An example of this would be a list of inline policies.
    The value can simply be appended to the inline policies for an AWS account.
Merge:
    That means the resource value must be merged (for lack of a better term) with the new value.
    This is used for attributes that are a list[dict] or a dict
      where the definition can only be defined once on an account.
    Example list[dict]:
        Adding an AWS tag to a resource.
        If a user wants to add a new tag and the tag key already exists for an account
            the existing value must be replaced with the new value
    Example dict:
        Adding permissions to an AWS managed policy.
        A managed policy only has a single policy document that contains a list of statements.
        To add permissions requires adding the permissions in the request to the policy document statements.
        If ManagedPolicyProperties.policy_document the permissions must be added to each policy document
            if the policy document's included accounts has at least 1 of the accounts defined in the request.
Replace:
    That means the resource value must be replaced with the new value.
    It is used for primitives (int, str, bool, etc).
    An example of this is the description of a role.
    If the description has changed it must be replaced.
"""


class TypeAheadFieldHelper(Base):
    __tablename__ = "typeahead_field_helper"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    query_param_key = Column(String, nullable=True)
    provider = Column(TrustedProvider, nullable=False)

    __table_args__ = (
        Index("typeahead_provider_idx", "provider"),
        Index("uix_typeahead_provider_name", "provider", "name", unique=True),
        Index("uix_typeahead_provider_endpoint", "provider", "endpoint", unique=True),
    )


class RequestType(SoftDeleteMixin, Base):
    __tablename__ = "request_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    # This is the full list of templates types that are supported by this request type
    supported_template_types = Column(ARRAY(String), nullable=False)
    # This is the subset that are actually available to the tenant.
    # For example, if SSO isn't set up.
    # Permission sets are supported for the request type but not for the tenant until SSO is configured.
    template_types = Column(ARRAY(String), nullable=False)
    template_attribute = Column(String, nullable=False)
    apply_attr_behavior = Column(ApplyAttrBehavior, nullable=False)

    tenant = relationship("Tenant")
    change_types = relationship(
        "ChangeType",
        back_populates="request_type",
        uselist=True,
        order_by="ChangeType.name",
    )

    __table_args__ = (
        Index("request_type_tenant_provider_idx", "tenant_id", "provider"),
        Index("uix_request_type_tp_name", "tenant_id", "provider", "name", unique=True),
    )

    def dict(self):
        # Be sure to normalize supported_template_types to list[dict[name, template_type]]
        response = {
            "id": str(self.id),
        }
        return response

    async def delete(self):
        async with ASYNC_PG_SESSION() as session:
            stmt = (
                update(ChangeType)
                .where(ChangeType.request_type_id == self.id)
                .values(deleted=True, deleted_at=datetime.utcnow())
            )
            await session.execute(stmt)

            self.deleted = True
            self.deleted_at = datetime.utcnow()
            session.add(self)
            await session.commit()

    async def reinitialize(self):
        """Un-Delete the request type and all change types associated with it.

        This can happen when the tenant had no supported template types but now they do.
        """

        async with ASYNC_PG_SESSION() as session:
            stmt = (
                update(ChangeType)
                .where(ChangeType.request_type_id == self.id)
                .values(deleted=False, deleted_at=None)
            )
            await session.execute(stmt)

            self.updated_at = datetime.utcnow()
            self.updated_by = "Noq"
            self.deleted_at = None
            self.deleted = False
            session.add(self)
            await session.commit()


class ChangeType(SoftDeleteMixin, Base):
    __tablename__ = "change_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type_id = Column(
        UUID(as_uuid=True), ForeignKey("request_type.id"), nullable=False
    )
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)

    request_type = relationship("RequestType", back_populates="change_types")
    change_fields = relationship(
        "ChangeField",
        back_populates="change_type",
        uselist=True,
        order_by="ChangeField.change_element",
        cascade="all, delete-orphan",
    )
    change_template = relationship(
        "ChangeTypeTemplate",
        back_populates="change_type",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ct_request_type_idx", "request_type_id"),
        Index("uix_change_type_request_name", "request_type_id", "name", unique=True),
    )

    def dict(self):
        response = {
            "id": str(self.id),
        }
        return response


class ChangeField(Base):
    __tablename__ = "change_field"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_type_id = Column(
        UUID(as_uuid=True), ForeignKey("change_type.id"), nullable=False
    )
    change_element = Column(Integer, nullable=False)
    field_key = Column(String, nullable=False)
    field_type = Column(FieldType, nullable=False)
    field_text = Column(String, nullable=False)
    description = Column(String, nullable=False)
    allow_none = Column(Boolean, nullable=False)
    allow_multiple = Column(Boolean, nullable=False)
    max_char = Column(Integer, nullable=True)
    validation_regex = Column(String, nullable=True)
    typeahead_field_helper_id = Column(
        UUID(as_uuid=True), ForeignKey("typeahead_field_helper.id")
    )
    # list(dict(option_text: str, option_value: str))
    # This works the same for the typeaheads API response under the data key
    options = Column(ARRAY(JSON), nullable=True)

    # Need to determine where this should be cast to the correct type
    # Probably in the dict method
    default_value = Column(String, nullable=True)

    typeahead = relationship("TypeAheadFieldHelper")
    change_type = relationship("ChangeType", back_populates="change_fields")

    __table_args__ = (
        Index("change_field_change_type_idx", "change_type_id"),
        Index(
            "uix_change_type_element", "change_type_id", "change_element", unique=True
        ),
    )

    def dict(self):
        response = {
            "id": str(self.id),
        }
        return response


class ChangeTypeTemplate(Base):
    __tablename__ = "change_type_template"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_type_id = Column(
        UUID(as_uuid=True), ForeignKey("change_type.id"), nullable=False
    )
    template = Column(String, nullable=False)

    change_type = relationship("ChangeType", back_populates="change_template")

    __table_args__ = (Index("uix_change_type_id_idx", "change_type_id", unique=True),)

    def dict(self):
        return {
            "id": str(self.id),
            "template": self.template,
        }
