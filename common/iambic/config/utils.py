import asyncio
import json
import sys
from collections import defaultdict
from typing import Optional

from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates
from sqlalchemy import and_, cast, delete, not_, select

from common.config import config as saas_config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.dynamic_config import load_iambic_config
from common.iambic.config.models import (
    TenantProvider,
    TenantProviderDefinition,
    TrustedProvider,
)
from common.iambic.templates.models import IambicTemplateProviderDefinition
from common.iambic.utils import get_iambic_repo
from common.lib.iambic.git import get_iambic_repo_path
from common.pg_core.utils import bulk_add, bulk_delete
from common.tenants.models import Tenant

log = saas_config.get_logger()


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
        if not template_id and exclude_aws_org and (not name or name == "aws"):
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
    tenant = await Tenant.get_by_name(tenant_name)
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

    try:
        # At some point we will support multiple repos and this is a way to futureproof
        iambic_repos = await get_iambic_repo(tenant_name)
        if not isinstance(iambic_repos, list):
            iambic_repos = [iambic_repos]
    except KeyError as err:
        log.error(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "tenant": tenant_name,
                "error": str(err),
            }
        )
        return

    for repo in iambic_repos:
        repo_dir = get_iambic_repo_path(tenant_name, repo.repo_name)
        try:
            config = await load_iambic_config(repo_dir)
        except ValueError as err:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "repo": repo.repo_name,
                    "tenant": tenant_name,
                    "error": str(err),
                }
            )

        # Collect provider definitions from the template repo
        azure_ad_templates = load_templates(
            await gather_templates(repo_dir, "AzureAD"), use_multiprocessing=False
        )
        okta_templates = load_templates(
            await gather_templates(repo_dir, "Okta"), use_multiprocessing=False
        )
        google_workspace_templates = load_templates(
            await gather_templates(repo_dir, "GoogleWorkspace"),
            use_multiprocessing=False,
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
