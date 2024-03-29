import asyncio
import json
from collections import defaultdict
from typing import Optional

from deepdiff import DeepDiff
from sqlalchemy import and_, cast, delete, not_, select

from common.config import config as saas_config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import (
    TenantProvider,
    TenantProviderDefinition,
    TrustedProvider,
)
from common.iambic.git.models import IambicRepo
from common.iambic.interface import IambicConfigInterface
from common.iambic.templates.models import IambicTemplateProviderDefinition
from common.pg_core.utils import bulk_add, bulk_delete
from common.tenants.models import Tenant

log = saas_config.get_logger(__name__)


async def list_tenant_providers(tenant_id: int) -> list[TenantProvider]:
    """Retrieve all trusted IAMbic providers enabled on the tenant"""
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(TenantProvider)
            .filter(TenantProvider.tenant_id == tenant_id)  # noqa: E712
            .order_by(TenantProvider.provider, TenantProvider.sub_type)
        )
        items = await session.execute(stmt)
    return items.scalars().all()


async def list_tenant_provider_definitions(
    tenant_id: int,
    provider: Optional[str] = None,
    name: Optional[str] = None,
    sub_type: Optional[str] = None,
    template_id: Optional[str] = None,
    exclude_aws_org: Optional[bool] = True,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
) -> list[TenantProviderDefinition]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(TenantProviderDefinition).filter(
            TenantProviderDefinition.tenant_id == tenant_id
        )  # noqa: E712
        if template_id:
            stmt = stmt.join(
                IambicTemplateProviderDefinition,
                TenantProviderDefinition.id
                == IambicTemplateProviderDefinition.tenant_provider_definition_id,
            ).filter(IambicTemplateProviderDefinition.iambic_template_id == template_id)

        if not template_id and sub_type:
            stmt = stmt.filter(TenantProviderDefinition.sub_type == sub_type)
        elif not template_id and exclude_aws_org and (not name or name == "aws"):
            if not name:
                stmt = stmt.filter(
                    not_(
                        and_(
                            TenantProviderDefinition.provider
                            == cast("aws", TrustedProvider),
                            TenantProviderDefinition.sub_type == "organizations",
                        )
                    )
                )
            else:
                stmt = stmt.filter(TenantProviderDefinition.sub_type != "organizations")
        if provider:
            stmt = stmt.filter(
                TenantProviderDefinition.provider == cast(provider, TrustedProvider)
            )  # noqa: E712
        if name:
            stmt = stmt.filter(
                TenantProviderDefinition.name.ilike(f"%{name}%")
            )  # noqa: E712

        if provider:
            stmt = stmt.order_by(TenantProviderDefinition.name)
        else:
            stmt = stmt.order_by(
                TenantProviderDefinition.provider, TenantProviderDefinition.name
            )

        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)
    return items.scalars().all()


async def update_tenant_providers_and_definitions(tenant_name: str):
    # This is super hacky, and we should be using the config object to do all of this
    # Unfortunately, we don't currently have a way to get providers that are stored in a secret
    tenant = await Tenant.get_by_name_nocache(tenant_name)
    if not tenant:
        log.error("Not a valid tenant", tenant=tenant_name)
        return

    iambic_repos = await IambicRepo.get_all_tenant_repos(tenant_name)
    if not iambic_repos:
        log.error(
            {
                "message": "No valid IAMbic repos found for tenant",
                "tenant": tenant.name,
            }
        )
        return

    new_definitions = []
    deleted_definitions = []
    new_providers = []
    deleted_providers = []

    existing_providers = await list_tenant_providers(tenant.id)
    existing_providers = {
        f"{provider.provider}-{provider.sub_type}": provider
        for provider in existing_providers
    }
    repo_providers = {}
    template_repo_definitions = defaultdict(dict)

    # Collect provider definitions currently in the DB
    raw_existing_definitions = await list_tenant_provider_definitions(
        tenant.id, exclude_aws_org=False
    )
    existing_definitions = defaultdict(dict)
    for existing_definition in raw_existing_definitions:
        existing_definitions[
            f"{existing_definition.provider}-{existing_definition.sub_type}"
        ][existing_definition.name] = existing_definition

    for iambic_repo in iambic_repos:
        iambic_config_interface = IambicConfigInterface(iambic_repo)
        # Collect provider definitions from the template repo
        azure_ad_templates = await iambic_config_interface.load_templates(
            await iambic_config_interface.gather_templates("AzureAD"),
        )
        okta_templates = await iambic_config_interface.load_templates(
            await iambic_config_interface.gather_templates("Okta")
        )
        google_workspace_templates = await iambic_config_interface.load_templates(
            await iambic_config_interface.gather_templates("GoogleWorkspace")
        )

        # Handling Azure AD and Okta
        generic_template_definitions = [
            {"provider": "azure_ad", "templates": azure_ad_templates},
            {"provider": "okta", "templates": okta_templates},
        ]
        for template_definitions in generic_template_definitions:
            provider = template_definitions["provider"]
            for template in template_definitions["templates"]:
                sub_type = ""
                base_key = f"{provider}-{sub_type}"

                repo_providers[base_key] = TenantProvider(
                    tenant_id=tenant.id, provider=provider
                )
                template_repo_definitions[base_key].setdefault(
                    template.idp_name,
                    {"idp_name": template.idp_name, "provider": provider},
                )

        # Handling Google Workspace
        for template in google_workspace_templates:
            domain = template.properties.domain
            provider = "google_workspace"
            sub_type = ""
            base_key = f"{provider}-{sub_type}"
            repo_providers[base_key] = TenantProvider(
                tenant_id=tenant.id, provider=provider
            )
            template_repo_definitions[base_key].setdefault(
                domain, {"domain": domain, "provider": provider}
            )

        iambic_config = await iambic_config_interface.get_iambic_config()
        # Handling AWS accounts and orgs
        if iambic_config.aws and iambic_config.aws.accounts:
            provider = "aws"
            for account in iambic_config.aws.accounts:
                sub_type = "accounts"
                base_key = f"{provider}-{sub_type}"
                definition = {
                    "provider": provider,
                    "sub_type": sub_type,
                    "account_id": account.account_id,
                    "account_name": account.account_name,
                    "variables": [
                        {"key": "account_id", "value": account.account_id},
                        {"key": "account_name", "value": account.account_name},
                    ],
                }
                if account.org_id:
                    definition["org_id"] = account.org_id
                if account.variables:
                    definition["variables"].extend(
                        [json.loads(var.json()) for var in account.variables]
                    )
                definition["preferred_identifier"] = account.preferred_identifier
                definition["all_identifiers"] = list(account.all_identifiers)

                repo_providers[base_key] = TenantProvider(
                    tenant_id=tenant.id, provider=provider, sub_type=sub_type
                )
                template_repo_definitions[base_key][str(account)] = definition

            for org in iambic_config.aws.organizations:
                sub_type = "organizations"
                base_key = f"{provider}-{sub_type}"
                definition = {
                    "provider": provider,
                    "sub_type": sub_type,
                    "org_id": org.org_id,
                    "org_account_id": org.org_account_id,
                }
                if org.org_name:
                    definition["org_name"] = org.org_name
                if org.identity_center:
                    definition["identity_center"] = json.loads(
                        org.identity_center.json()
                    )

                repo_providers[base_key] = TenantProvider(
                    tenant_id=tenant.id, provider=provider, sub_type=sub_type
                )
                template_repo_definitions["aws"][str(org)] = definition

    # Generate list of providers to delete
    for provider_full, provider_obj in existing_providers.items():
        if provider_full not in repo_providers:
            deleted_providers.append(provider_obj)

    # Generate list of providers to add
    for provider_full, provider_obj in repo_providers.items():
        if provider_full not in existing_providers:
            new_providers.append(provider_obj)

    # Generate list of provider definitions to delete
    for provider_full, definitions in existing_definitions.items():
        for name, definition in definitions.items():
            if not template_repo_definitions.get(provider_full, {}).get(name):
                deleted_definitions.append(definition)

    # Generate list of provider definitions to add
    for provider_full, definitions in template_repo_definitions.items():
        for name, definition in definitions.items():
            provider = definition.pop("provider")
            sub_type = definition.pop("sub_type", "")
            existing_def = existing_definitions.get(provider_full, {}).get(name)
            if not existing_def:
                new_definitions.append(
                    TenantProviderDefinition(
                        tenant_id=tenant.id,
                        provider=provider,
                        sub_type=sub_type,
                        name=name,
                        definition=definition,
                    )
                )
            elif bool(DeepDiff(existing_def.definition, definition, ignore_order=True)):
                existing_def.definition = definition
                await existing_def.write()

    if deleted_definitions:
        await bulk_delete(deleted_definitions)
    if deleted_providers:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = delete(TenantProviderDefinition).where(
                    and_(
                        TenantProviderDefinition.tenant_id == tenant.id,
                        TenantProviderDefinition.provider.in_(
                            [dp.provider for dp in deleted_providers]
                        ),
                    )
                )
                await session.execute(stmt)

        await bulk_delete(deleted_providers)

    create_tasks = []
    if new_definitions:
        create_tasks.append(bulk_add(new_definitions))
    if new_providers:
        create_tasks.append(bulk_add(new_providers))

    if create_tasks:
        await asyncio.gather(*create_tasks)
