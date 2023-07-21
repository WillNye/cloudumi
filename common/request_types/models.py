import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql.schema import Table

from common.config import config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant  # noqa: F401

if TYPE_CHECKING:
    from common.users.models import User
else:
    User = object

log = config.get_logger(__name__)

FieldType = ENUM(
    "TextBox",
    "TypeAhead",
    "EnforcedTypeAhead",
    "TypeAheadTemplateRef",
    "CheckBox",
    "Choice",
    name="FieldTypeEnum",
)
ProviderDefinitionField = ENUM(
    "Allow One", "Allow Multiple", "Allow None", name="ProviderDefinitionFieldEnum"
)
"""
Allow One
    Example usage
      - With a IAM Managed Policy attachments an arn is provided that is account specific
Allow Multiple
    The most common scenario with things like IAM Role policies
Allow None
    Used for templates and template attributes without an access rule
    If there is no access rule an attr that scopes by provider definition id is pointless
    Example
      - Request to add permissions to a PermissionSet
"""
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


change_type_group_association = Table(
    "change_type_group_association",
    Base.metadata,
    Column("change_type_id", UUID(as_uuid=True), ForeignKey("change_type.id")),
    Column("group_id", UUID(as_uuid=True), ForeignKey("groups.id")),
)

change_type_user_association = Table(
    "change_type_user_association",
    Base.metadata,
    Column("change_type_id", UUID(as_uuid=True), ForeignKey("change_type.id")),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
)

change_type_iambic_template_provider_definition_association = Table(
    "change_type_iambic_template_provider_definition_association",
    Base.metadata,
    Column("change_type_id", UUID(as_uuid=True), ForeignKey("change_type.id")),
    Column(
        "iambic_template_provider_definition_id",
        UUID(as_uuid=True),
        ForeignKey("iambic_template_provider_definition.id"),
    ),
)

user_favorited_change_type_association = Table(
    "user_favorited_change_type_association",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column(
        "change_type_id",
        UUID(as_uuid=True),
        ForeignKey("change_type.id"),
    ),
    Index("ufcta_user_favorite_idx", "user_id", "change_type_id"),
)

user_favorited_express_access_request_association = Table(
    "user_favorited_express_access_request_association",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column(
        "express_access_request_id",
        UUID(as_uuid=True),
        ForeignKey("express_access_request.id"),
    ),
    Index("ufeara_user_favorite_idx", "user_id", "express_access_request_id"),
)


class TypeAheadFieldHelper(Base):
    __tablename__ = "typeahead_field_helper"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    query_param_key = Column(String, nullable=True)
    provider = Column(TrustedProvider, nullable=False)
    # This is used to expose a schema for the change template builder
    iambic_template_type = Column(String, nullable=True)

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
        response = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "provider": self.provider,
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


class ExpressAccessRequest(SoftDeleteMixin, Base):
    """
    This is essentially a pre-populated permission request change type
    """

    __tablename__ = "express_access_request"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_type_id = Column(
        UUID(as_uuid=True), ForeignKey("change_type.id"), nullable=False
    )
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    field_values = Column(JSONB, nullable=False)
    suggest_to_all = Column(Boolean, default=False)

    tenant = relationship("Tenant")
    change_type = relationship("ChangeType")
    favorited_by = relationship(
        "User",
        secondary=user_favorited_express_access_request_association,
        back_populates="favorited_access_requests",
    )

    __table_args__ = (
        Index("ear_change_type_idx", "tenant_id", "change_type_id"),
        Index(
            "ear_suggest_to_all_idx",
            "tenant_id",
            "suggest_to_all",
            "name",
            "change_type_id",
        ),
    )

    @classmethod
    async def favorite(
        cls, tenant_id: int, express_access_request_id: str, user: User
    ) -> "ExpressAccessRequest":
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(cls)
                    .filter(
                        cls.id == express_access_request_id, cls.tenant_id == tenant_id
                    )
                    .options(selectinload(cls.favorited_by))
                )
                items = await session.execute(stmt)
                express_access_request = items.scalars().unique().one_or_none()
                if not express_access_request:
                    return

                express_access_request.favorited_by.append(user)
                session.add(express_access_request)
                await session.commit()

        return express_access_request

    @classmethod
    async def unfavorite(
        cls, tenant_id: int, express_access_request_id: str, user: User
    ) -> "ExpressAccessRequest":
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(cls)
                    .filter(
                        cls.id == express_access_request_id, cls.tenant_id == tenant_id
                    )
                    .options(selectinload(cls.favorited_by))
                )
                items = await session.execute(stmt)
                express_access_request = items.scalars().unique().one_or_none()
                if not express_access_request:
                    return

                express_access_request.favorited_by.remove(user)
                session.add(express_access_request)
                await session.commit()

        return express_access_request


class ChangeType(SoftDeleteMixin, Base):
    __tablename__ = "change_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type_id = Column(
        UUID(as_uuid=True), ForeignKey("request_type.id"), nullable=False
    )
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    template_attribute = Column(String, nullable=True)
    apply_attr_behavior = Column(ApplyAttrBehavior, nullable=True)
    provider_definition_field = Column(ProviderDefinitionField, nullable=True)
    tenant = relationship("Tenant")
    suggest_to_all = Column(Boolean, default=False)

    # This is the full list of templates types that are supported by this request type
    supported_template_types = Column(ARRAY(String), nullable=False)

    # This is the subset that are actually available to the tenant.
    # For example, if SSO isn't set up.
    # Permission sets are supported for the change type but not for the tenant until SSO is configured.
    template_types = Column(ARRAY(String), nullable=False)

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

    included_groups = relationship(
        "Group",
        secondary=change_type_group_association,
        back_populates="associated_change_types",
    )
    included_users = relationship(
        "User",
        secondary=change_type_user_association,
        back_populates="associated_change_types",
    )
    included_iambic_template_provider_definition = relationship(
        "IambicTemplateProviderDefinition",
        secondary=change_type_iambic_template_provider_definition_association,
        back_populates="associated_change_types",
    )
    favorited_by = relationship(
        "User",
        secondary=user_favorited_change_type_association,
        back_populates="favorited_change_types",
    )

    __table_args__ = (
        Index("ct_tenant_idx", "id", "tenant_id"),
        Index(
            "ct_suggested_change_type_idx", "id", "tenant_id", "name", "suggest_to_all"
        ),
        Index("ct_request_type_idx", "tenant_id", "request_type_id"),
    )

    def dict(self):
        response = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "request_type_id": str(self.request_type_id),
            "included_iambic_template_provider_definition": [
                x.dict() for x in self.included_iambic_template_provider_definition
            ],
            "provider_definition_field": self.provider_definition_field,
        }
        return response

    async def reinitialize(self):
        """Un-Delete the change type.

        This can happen when the tenant had no supported template types but now they do.
        """
        self.updated_at = datetime.utcnow()
        self.updated_by = "Noq"
        self.deleted_at = None
        self.deleted = False
        await self.write()

    @classmethod
    async def favorite(
        cls, tenant_id: int, change_type_id: str, user: User
    ) -> "ChangeType":
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(cls)
                    .filter(cls.id == change_type_id, cls.tenant_id == tenant_id)
                    .options(selectinload(cls.favorited_by))
                )
                items = await session.execute(stmt)
                change_type = items.scalars().unique().one_or_none()
                if not change_type:
                    return

                change_type.favorited_by.append(user)
                session.add(change_type)
                await session.commit()

        return change_type

    @classmethod
    async def unfavorite(
        cls, tenant_id: int, change_type_id: str, user: User
    ) -> "ChangeType":
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = (
                    select(cls)
                    .filter(cls.id == change_type_id, cls.tenant_id == tenant_id)
                    .options(selectinload(cls.favorited_by))
                )
                items = await session.execute(stmt)
                change_type = items.scalars().unique().one_or_none()
                if not change_type:
                    return

                change_type.favorited_by.remove(user)
                session.add(change_type)
                await session.commit()

        return change_type


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
        Index("uix_change_type_field_key", "change_type_id", "field_key", unique=True),
    )

    def self_service_dict(self):
        response = {
            "id": str(self.id),
            "change_type_id": str(self.change_type_id),
            "change_element": self.change_element,
            "field_key": self.field_key,
            "field_type": str(self.field_type),
            "field_text": self.field_text,
            "description": self.description,
            "allow_none": self.allow_none,
            "allow_multiple": self.allow_multiple,
        }
        if self.options:
            response["options"] = [option["option_text"] for option in self.options]
        if self.typeahead:
            response["typeahead"] = {
                "endpoint": self.typeahead.endpoint,
                "query_param_key": self.typeahead.query_param_key,
            }
        for optional_field in ["default_value", "max_char", "validation_regex"]:
            if field_val := getattr(self, optional_field):
                response[optional_field] = field_val

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
