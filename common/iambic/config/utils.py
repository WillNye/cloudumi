import asyncio
import json
from collections import defaultdict

from iambic.config.dynamic_config import Config as IambicConfig
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates
from sqlalchemy import and_, cast, not_, select

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import (
    TenantProvider,
    TenantProviderDefinition,
    TrustedProvider,
)
from common.pg_core.utils import bulk_add, bulk_delete
from common.tenants.models import Tenant


async def list_tenant_providers(tenant: str) -> list[TenantProvider]:
    """Retrieve all trusted IAMbic providers enabled on the tenant"""
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(TenantProvider)
            .join(TenantProvider.tenant)
            .filter(Tenant.name == tenant)  # noqa: E712
        )
        items = await session.execute(stmt)
    return items.scalars().all()


async def list_tenant_provider_definitions(
    tenant: str, provider: str = None, name: str = None, exclude_aws_org: bool = True
) -> list[TenantProviderDefinition]:
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(TenantProviderDefinition)
            .join(TenantProviderDefinition.tenant)
            .filter(Tenant.name == tenant)  # noqa: E712
        )
        if exclude_aws_org and (not name or name == "aws"):
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
        items = await session.execute(stmt)
    return items.scalars().all()


async def update_tenant_providers_and_definitions(
    tenant: Tenant, config: IambicConfig, repo_dir: str
):
    # This is super hacky, and we should be using the config object to do all of this
    # Unfortunately, we don't currently have a way to get providers that are stored in a secret
    new_definitions = []
    deleted_definitions = []
    new_providers = []
    deleted_providers = []

    existing_providers = await list_tenant_providers(tenant.name)
    existing_providers = {
        f"{provider.provider}-{provider.sub_type}": provider
        for provider in existing_providers
    }
    repo_providers = {}
    template_repo_definitions = defaultdict(dict)

    # Collect provider definitions currently in the DB
    raw_existing_definitions = await list_tenant_provider_definitions(
        tenant.name, exclude_aws_org=False
    )
    existing_definitions = defaultdict(dict)
    for existing_definition in raw_existing_definitions:
        existing_definitions[
            f"{existing_definition.provider}-{existing_definition.sub_type}"
        ][existing_definition.name] = existing_definition

    # Collect provider definitions from the template repo
    azure_ad_templates = load_templates(await gather_templates(repo_dir, "AzureAD"))
    okta_templates = load_templates(await gather_templates(repo_dir, "Okta"))
    google_workspace_templates = load_templates(
        await gather_templates(repo_dir, "GoogleWorkspace")
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
            if template.idp_name == "Default":
                continue
            repo_providers[base_key] = TenantProvider(
                tenant_id=tenant.id, provider=provider
            )
            template_repo_definitions[base_key].setdefault(
                template.idp_name, {"idp_name": template.idp_name, "provider": provider}
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

    # Handling AWS accounts and orgs
    if config.aws and config.aws.accounts:
        provider = "aws"
        for account in config.aws.accounts:
            sub_type = "accounts"
            base_key = f"{provider}-{sub_type}"
            definition = {
                "provider": provider,
                "sub_type": sub_type,
                "account_id": account.account_id,
                "account_name": account.account_name,
            }
            if account.org_id:
                definition["org_id"] = account.org_id
            if account.variables:
                definition["variables"] = [
                    json.loads(var.json()) for var in account.variables
                ]

            repo_providers[base_key] = TenantProvider(
                tenant_id=tenant.id, provider=provider, sub_type=sub_type
            )
            template_repo_definitions[base_key][str(account)] = definition

        for org in config.aws.organizations:
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
                definition["identity_center"] = json.loads(org.identity_center.json())

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
            if not existing_definitions.get(provider_full, {}).get(name):
                new_definitions.append(
                    TenantProviderDefinition(
                        tenant_id=tenant.id,
                        provider=provider,
                        sub_type=sub_type,
                        name=name,
                        definition=definition,
                    )
                )

    create_tasks = []
    delete_tasks = []

    if deleted_definitions:
        delete_tasks.append(bulk_delete(deleted_definitions))
    if deleted_providers:
        delete_tasks.append(bulk_delete(deleted_providers))

    if new_definitions:
        create_tasks.append(bulk_add(new_definitions))
    if new_providers:
        create_tasks.append(bulk_add(new_providers))

    if delete_tasks:
        await asyncio.gather(*delete_tasks)
    if create_tasks:
        await asyncio.gather(*create_tasks)
