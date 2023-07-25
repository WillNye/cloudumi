import uuid
from dataclasses import dataclass
from typing import Optional, Type

from iambic.core.iambic_plugin import ProviderPlugin
from iambic.core.models import BaseTemplate, Variable
from iambic.plugins.v0_1_0.aws.iambic_plugin import IAMBIC_PLUGIN as AWS_IAMBIC_PLUGIN
from iambic.plugins.v0_1_0.azure_ad.iambic_plugin import (
    IAMBIC_PLUGIN as AZURE_AD_IAMBIC_PLUGIN,
)
from iambic.plugins.v0_1_0.google_workspace.iambic_plugin import (
    IAMBIC_PLUGIN as GOOGLE_WORKSPACE_IAMBIC_PLUGIN,
)
from iambic.plugins.v0_1_0.google_workspace.iambic_plugin import GoogleWorkspaceConfig
from iambic.plugins.v0_1_0.okta.iambic_plugin import IAMBIC_PLUGIN as OKTA_IAMBIC_PLUGIN
from pydantic.types import SecretStr
from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from common.config import config
from common.pg_core.models import Base
from common.tenants.models import Tenant

log = config.get_logger(__name__)


@dataclass
class TrustedProviderResolver:
    provider: str
    template_type_prefix: str
    iambic_plugin: ProviderPlugin
    included_providers_attribute: Optional[str] = None
    excluded_providers_attribute: Optional[str] = None
    template_provider_attribute: Optional[str] = None
    provider_config_definition_attribute: Optional[str] = None

    @property
    def provider_defined_in_template(self) -> bool:
        return bool(self.template_provider_attribute)

    @staticmethod
    def get_name_from_iambic_provider_config(provider_config):
        return str(provider_config)

    @property
    def template_classes(self):
        return self.iambic_plugin.templates

    @property
    def template_map(self) -> dict[str, Type[BaseTemplate]]:
        return {
            template.__fields__["template_type"].default: template
            for template in self.template_classes
        }

    def get_name_from_iambic_template(self, template):
        if not self.template_provider_attribute:
            return None

        name = template
        for attr in self.template_provider_attribute.split("."):
            name = getattr(name, attr, None)
            if name is None:
                return name

        return name

    def get_provider_definitions_from_config(self, config):
        if not self.provider_config_definition_attribute:
            return []

        resp = getattr(config, self.provider)
        for attr in self.provider_config_definition_attribute.split("."):
            resp = getattr(resp, attr, None)
            if resp is None:
                return resp

        return resp


TRUSTED_PROVIDER_RESOLVERS = [
    TrustedProviderResolver(
        provider="aws",
        template_type_prefix="NOQ::AWS",
        provider_config_definition_attribute="accounts",
        iambic_plugin=AWS_IAMBIC_PLUGIN,
        included_providers_attribute="included_accounts",
        excluded_providers_attribute="excluded_accounts",
    ),
    TrustedProviderResolver(
        provider="azure_ad",
        template_type_prefix="NOQ::AzureAD",
        template_provider_attribute="idp_name",
        iambic_plugin=AZURE_AD_IAMBIC_PLUGIN,
    ),
    TrustedProviderResolver(
        provider="google_workspace",
        template_type_prefix="NOQ::GoogleWorkspace",
        template_provider_attribute="properties.domain",
        iambic_plugin=GOOGLE_WORKSPACE_IAMBIC_PLUGIN,
    ),
    TrustedProviderResolver(
        provider="okta",
        template_type_prefix="NOQ::Okta",
        template_provider_attribute="idp_name",
        iambic_plugin=OKTA_IAMBIC_PLUGIN,
    ),
]

TRUSTED_PROVIDER_RESOLVER_MAP: dict[str, TrustedProviderResolver] = {
    tpr.provider: tpr for tpr in TRUSTED_PROVIDER_RESOLVERS
}

# When a table using this column is created as part of a migration,
#   be sure to set create_type=False for that field in the migration.py
TrustedProvider = ENUM(*list(TRUSTED_PROVIDER_RESOLVER_MAP.keys()), name="ProviderEnum")


class TenantProvider(Base):
    __tablename__ = "tenant_provider"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    sub_type = Column(String, nullable=False, default="")

    tenant = relationship(Tenant)

    __table_args__ = (
        Index("tp_tenant_idx", "tenant_id"),
        Index("uix_tp_idx", "tenant_id", "provider", "sub_type", unique=True),
    )


class TenantProviderDefinition(Base):
    __tablename__ = "tenant_provider_definition"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenant.id"), nullable=False)
    provider = Column(TrustedProvider, nullable=False)
    sub_type = Column(String, nullable=True)
    name = Column(String, nullable=False)
    definition = Column(JSON, nullable=True)

    tenant = relationship(Tenant)

    __table_args__ = (
        Index("tpd_tenant_idx", "tenant_id"),
        Index("tpd_tenant_provider_idx", "tenant_id", "provider"),
        Index("uix_tpd_idx", "tenant_id", "provider", "sub_type", "name", unique=True),
    )

    @property
    def variables(self) -> list[Variable]:
        # This is using IAMbic definitions for `account_id`, `account_name` for parity
        # with what is in their AWS org. We are not using SaaS-defined definitions here.
        variables = [Variable(**v) for v in self.definition.get("variables", [])]
        if self.provider == "aws" and self.sub_type == "accounts":
            variables.extend(
                [
                    Variable(key="account_id", value=self.definition["account_id"]),
                    Variable(key="account_name", value=self.definition["account_name"]),
                ]
            )

        return variables

    @property
    def preferred_identifier(self) -> str:
        return self.definition.get("preferred_identifier", self.name)

    @property
    def all_identifiers(self) -> list[str]:
        return self.definition.get("all_identifiers", [self.name])

    def loaded_iambic_provider(self):
        """Creates and returns an instance of the iambic provider class with the definition.

        The benefit of this is you don't need to load the provider repo and config making it much more performant.
        """

        field_attr = self.sub_type
        provider_config = TRUSTED_PROVIDER_RESOLVER_MAP[
            self.provider
        ].iambic_plugin.provider_config
        if provider_config == GoogleWorkspaceConfig:
            field_attr = "workspaces"
        elif not field_attr:
            field_attr = "organizations"

        iambic_provider = provider_config.__fields__[field_attr].type_
        definition = self.definition
        definition.pop("all_identifiers", None)
        definition.pop("preferred_identifier", None)

        if provider_config == GoogleWorkspaceConfig:
            definition = {"subjects": [definition]}

        for field_name, field_obj in iambic_provider.__fields__.items():
            if field_obj.required:
                if field_obj.type_ in {str, SecretStr}:
                    default_val = ""
                else:
                    default_val = []
                definition.setdefault(field_name, default_val)

        return provider_config.__fields__[field_attr].type_(**definition)

    def self_service_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "provider": self.provider,
            "sub_type": self.sub_type,
            "definition": self.definition,
        }
