import asyncio
import sys
from collections import defaultdict
from datetime import datetime
from itertools import chain
from typing import Union

import pytz
from git import Repo
from iambic.core.git import retrieve_git_changes
from iambic.core.parser import load_templates
from iambic.core.utils import evaluate_on_provider, gather_templates
from sqlalchemy import and_, cast, delete, select, update
from sqlalchemy.orm import contains_eager

from common.config import config as saas_config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.dynamic_config import load_iambic_config
from common.iambic.config.models import (
    TRUSTED_PROVIDER_RESOLVER_MAP,
    TenantProviderDefinition,
    TrustedProvider,
)
from common.iambic.config.utils import list_tenant_provider_definitions
from common.iambic.templates.models import (
    IambicTemplate,
    IambicTemplateContent,
    IambicTemplateProviderDefinition,
)
from common.iambic.utils import get_iambic_repo
from common.lib.asyncio import NoqSemaphore
from common.lib.iambic.git import get_iambic_repo_path
from common.models import IambicRepoDetails
from common.pg_core.utils import bulk_add, bulk_delete
from common.tenants.models import Tenant

log = saas_config.get_logger()


async def create_tenant_templates_and_definitions(
    tenant: Tenant,
    iambic_config,
    repo: IambicRepoDetails,
    repo_dir: str,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    template_paths: list[str] = None,
):
    template_type_provider_map = {}
    iambic_templates = []
    iambic_template_content_list = []
    iambic_template_provider_definitions = []

    if not template_paths:
        template_paths = await gather_templates(repo_dir)

    log.info(
        {
            "message": "Creating templates",
            "tenant": tenant.name,
            "template_count": len(template_paths),
            "repo": repo.repo_name,
        }
    )

    # Collect provider definitions from the template repo
    for raw_iambic_template in load_templates(template_paths):
        provider = template_type_provider_map.get(raw_iambic_template.template_type)
        if not provider:
            for (
                trusted_provider,
                template_type_resolver,
            ) in TRUSTED_PROVIDER_RESOLVER_MAP.items():
                if raw_iambic_template.template_type.startswith(
                    template_type_resolver.template_type_prefix
                ):
                    provider = trusted_provider
                    template_type_provider_map[
                        raw_iambic_template.template_type
                    ] = provider
                    break

        if not provider:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "repo": repo.repo_name,
                    "tenant": tenant.name,
                    "template_type": raw_iambic_template.template_type,
                    "error": "Could not find provider for template type.",
                }
            )
            continue

        iambic_template = IambicTemplate(
            tenant=tenant,
            repo_name=repo.repo_name,
            file_path=str(raw_iambic_template.file_path).replace(repo_dir, ""),
            template_type=raw_iambic_template.template_type,
            provider=provider,
            resource_type=raw_iambic_template.resource_type,
            resource_id=raw_iambic_template.resource_id,
        )
        iambic_templates.append(iambic_template)

        iambic_template_content = IambicTemplateContent(
            tenant=tenant,
            iambic_template=iambic_template,
            content=raw_iambic_template.dict().get("properties", {}),
        )
        iambic_template_content_list.append(iambic_template_content)

        provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP.get(provider)
        if provider_resolver.provider_defined_in_template:
            pd_name = provider_resolver.get_name_from_iambic_template(
                raw_iambic_template
            )
            tpd = provider_definition_map[provider].get(pd_name)
            iambic_template_provider_definitions.append(
                IambicTemplateProviderDefinition(
                    tenant=tenant,
                    iambic_template=iambic_template,
                    tenant_provider_definition=tpd,
                )
            )
        else:
            provider_defs = provider_resolver.get_provider_definitions_from_config(
                iambic_config
            )
            for provider_def in provider_defs:
                if evaluate_on_provider(raw_iambic_template, provider_def, False):
                    pd_name = provider_resolver.get_name_from_iambic_provider_config(
                        provider_def
                    )
                    tpd = provider_definition_map[provider].get(pd_name)
                    iambic_template_provider_definitions.append(
                        IambicTemplateProviderDefinition(
                            tenant=tenant,
                            iambic_template=iambic_template,
                            tenant_provider_definition=tpd,
                        )
                    )

    if iambic_templates:
        await bulk_add(iambic_templates)
    if iambic_template_content_list:
        await bulk_add(iambic_template_content_list)
    if iambic_template_provider_definitions:
        await bulk_add(iambic_template_provider_definitions)


async def update_tenant_template(
    tenant: Tenant,
    iambic_config,
    repo: IambicRepoDetails,
    repo_dir: str,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    raw_iambic_template: IambicTemplate,
    provider: TrustedProvider,
) -> tuple[Union[str, None], list[IambicTemplateProviderDefinition]]:
    iambic_template_provider_definitions = []

    # Get the existing template with its provider definition references
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(IambicTemplate)
            .where(
                and_(
                    IambicTemplate.tenant_id == tenant.id,
                    IambicTemplate.provider == cast(provider, TrustedProvider),
                    IambicTemplate.resource_type == raw_iambic_template.resource_type,
                    IambicTemplate.resource_id == raw_iambic_template.resource_id,
                    IambicTemplate.template_type == raw_iambic_template.template_type,
                    IambicTemplate.repo_name == repo.repo_name,
                )
            )
            .outerjoin(
                IambicTemplateProviderDefinition,
                and_(
                    IambicTemplateProviderDefinition.iambic_template_id
                    == IambicTemplate.id
                ),
            )
            .options(contains_eager(IambicTemplate.provider_definition_refs))
        )
        result = await session.execute(stmt)
        iambic_template: IambicTemplate = result.scalars().unique().one_or_none()

    if not iambic_template:
        # This template isn't in the db so mark it for creation
        return raw_iambic_template.file_path, []

    file_path = str(raw_iambic_template.file_path).replace(repo_dir, "")
    if iambic_template.file_path != file_path:
        iambic_template.file_path = file_path
        await iambic_template.write()

    async with ASYNC_PG_SESSION() as session:
        stmt = (
            update(IambicTemplateContent)
            .where(
                and_(
                    IambicTemplateContent.iambic_template_id == iambic_template.id,
                    IambicTemplateContent.tenant_id == tenant.id,
                )
            )
            .values(content=raw_iambic_template.dict().get("properties", {}))
        )
        await session.execute(stmt)

    # Create a map of the template provider definitions already in the db
    # After we process the template we will remove any that are still in the map
    existing_provider_definition_id_map = {
        provider_def_ref.id: provider_def_ref
        for provider_def_ref in iambic_template.provider_definition_refs
    }

    provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP.get(provider)
    if provider_resolver.provider_defined_in_template:
        pd_name = provider_resolver.get_name_from_iambic_template(raw_iambic_template)
        tpd = provider_definition_map[provider].get(pd_name)
        if tpd.id in existing_provider_definition_id_map:
            # The reference already exists and is in the template so skip it
            existing_provider_definition_id_map.pop(tpd.id, None)
        else:
            iambic_template_provider_definitions.append(
                IambicTemplateProviderDefinition(
                    tenant_id=tenant.id,
                    iambic_template_id=iambic_template.id,
                    tenant_provider_definition_id=tpd.id,
                )
            )
    else:
        provider_defs = provider_resolver.get_provider_definitions_from_config(
            iambic_config
        )
        for provider_def in provider_defs:
            if evaluate_on_provider(raw_iambic_template, provider_def, False):
                pd_name = provider_resolver.get_name_from_iambic_provider_config(
                    provider_def
                )
                tpd = provider_definition_map[provider].get(pd_name)
                if tpd.id in existing_provider_definition_id_map:
                    # The reference already exists and is in the template so skip it
                    existing_provider_definition_id_map.pop(tpd.id, None)
                else:
                    iambic_template_provider_definitions.append(
                        IambicTemplateProviderDefinition(
                            tenant_id=tenant.id,
                            iambic_template_id=iambic_template.id,
                            tenant_provider_definition_id=tpd.id,
                        )
                    )

    # Remove any template provider definitions that were not evaluated using the template
    if existing_provider_definition_id_map:
        await bulk_delete(list(existing_provider_definition_id_map.values()))

    return None, iambic_template_provider_definitions


async def upsert_tenant_templates_and_definitions(
    tenant: Tenant,
    iambic_config,
    repo: IambicRepoDetails,
    repo_dir: str,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    template_paths: list[str],
):
    template_type_provider_map = {}
    update_tenant_template_semaphore = NoqSemaphore(update_tenant_template, 30)

    log.info(
        {
            "message": "Updating templates",
            "tenant": tenant.name,
            "template_count": len(template_paths),
            "repo": repo.repo_name,
        }
    )

    # Collect provider definitions from the template repo
    messages = []
    for raw_iambic_template in load_templates(template_paths):
        provider = template_type_provider_map.get(raw_iambic_template.template_type)
        if not provider:
            for (
                trusted_provider,
                template_type_resolver,
            ) in TRUSTED_PROVIDER_RESOLVER_MAP.items():
                if raw_iambic_template.template_type.startswith(
                    template_type_resolver.template_type_prefix
                ):
                    provider = trusted_provider
                    template_type_provider_map[
                        raw_iambic_template.template_type
                    ] = provider
                    break

        if not provider:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "repo": repo.repo_name,
                    "tenant": tenant.name,
                    "template_type": raw_iambic_template.template_type,
                    "error": "Could not find provider for template type.",
                }
            )
            continue

        messages.append(
            {
                "tenant": tenant,
                "iambic_config": iambic_config,
                "repo": repo,
                "repo_dir": repo_dir,
                "provider_definition_map": provider_definition_map,
                "raw_iambic_template": raw_iambic_template,
                "provider": provider,
            }
        )

    new_template_paths = []
    iambic_template_provider_definitions = []
    responses = await update_tenant_template_semaphore.process(messages)
    for response in responses:
        if response[0]:
            new_template_paths.append(response[0])
        elif response[1]:
            iambic_template_provider_definitions.append(response[1])

    tasks = []
    if new_template_paths:
        tasks.append(
            create_tenant_templates_and_definitions(
                tenant,
                iambic_config,
                repo,
                repo_dir,
                provider_definition_map,
                list(chain.from_iterable(new_template_paths)),
            )
        )
    if iambic_template_provider_definitions:
        tasks.append(
            bulk_add(list(chain.from_iterable(iambic_template_provider_definitions)))
        )

    if tasks:
        await asyncio.gather(*tasks)


async def delete_tenant_templates_and_definitions(
    tenant: Tenant,
    repo: IambicRepoDetails,
    repo_dir: str,
    template_paths: list[str],
):
    log.info(
        {
            "message": "Deleting templates",
            "tenant": tenant.name,
            "template_count": len(template_paths),
            "repo": repo.repo_name,
        }
    )

    deleted_template_paths = [
        str(template_path).replace(repo_dir, "") for template_path in template_paths
    ]
    if deleted_template_paths:
        # Get the existing template with its provider definition references
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                max_elem = 25
                for elem_offset in range(0, len(deleted_template_paths), max_elem):
                    path_chunk = deleted_template_paths[
                        elem_offset : elem_offset + max_elem
                    ]
                    stmt = delete(IambicTemplate).where(
                        and_(
                            IambicTemplate.tenant_id == tenant.id,
                            IambicTemplate.repo_name == repo.repo_name,
                            IambicTemplate.file_path.in_(path_chunk),
                        )
                    )
                    await session.execute(stmt)
                    await session.flush()


async def full_create_tenant_templates_and_definitions(
    tenant: Tenant, provider_definition_map: dict[dict[str, TenantProviderDefinition]]
):
    try:
        # At some point we will support multiple repos and this is a way to futureproof
        iambic_repos = await get_iambic_repo(tenant.name)
        if not isinstance(iambic_repos, list):
            iambic_repos = [iambic_repos]
    except KeyError as err:
        log.error(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "tenant": tenant.name,
                "error": str(err),
            }
        )
        return

    for repo in iambic_repos:
        repo_dir = get_iambic_repo_path(tenant.name, repo.repo_name)
        try:
            iambic_config = await load_iambic_config(repo_dir)
        except ValueError as err:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "repo": repo.repo_name,
                    "tenant": tenant.name,
                    "error": str(err),
                }
            )
            continue

        await create_tenant_templates_and_definitions(
            tenant,
            iambic_config,
            repo,
            repo_dir,
            provider_definition_map,
        )


async def sync_tenant_templates_and_definitions(tenant_name: str):
    tenant = await Tenant.get_by_name(tenant_name)
    provider_definition_map = defaultdict(dict)
    iambic_templates_last_parsed = datetime.utcnow()

    raw_existing_definitions = await list_tenant_provider_definitions(tenant.id)
    if not raw_existing_definitions:
        log.warning(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "message": "Unable to create tenant templates and definitions without provider definitions.",
                "tenant": tenant.name,
            }
        )
        return
    for existing_definition in raw_existing_definitions:
        provider_definition_map[existing_definition.provider][
            existing_definition.name
        ] = existing_definition

    if not tenant.iambic_templates_last_parsed:
        try:
            await full_create_tenant_templates_and_definitions(
                tenant, provider_definition_map
            )
            tenant.iambic_templates_last_parsed = iambic_templates_last_parsed
            await tenant.write()
        except Exception as err:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Unable to create tenant templates and definitions.",
                    "tenant": tenant.name,
                    "error": str(err),
                }
            )

        return

    # Return if not provider definitions
    templates_last_parsed = pytz.UTC.localize(tenant.iambic_templates_last_parsed)
    iambic_templates_last_parsed = datetime.utcnow()

    try:
        # At some point we will support multiple repos and this is a way to futureproof
        iambic_repos = await get_iambic_repo(tenant.name)
        if not isinstance(iambic_repos, list):
            iambic_repos = [iambic_repos]
    except KeyError as err:
        log.error(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "tenant": tenant.name,
                "error": str(err),
            }
        )
        return

    for repo in iambic_repos:
        repo_dir = get_iambic_repo_path(tenant.name, repo.repo_name)

        # Get all changes since last parsed
        git_repo = Repo(repo_dir)
        from_sha = None
        to_sha = None
        for commit in git_repo.iter_commits("main"):  # Correctly resolve default branch
            if commit.committed_datetime < templates_last_parsed:
                break

            if not to_sha:
                to_sha = commit.hexsha
            else:
                from_sha = commit.hexsha

        template_changes = await retrieve_git_changes(
            repo_dir, from_sha=from_sha, to_sha=to_sha
        )
        create_template_paths = []
        upsert_template_paths = []
        deleted_template_paths = []

        for git_diff in template_changes["new_files"]:
            create_template_paths.append(git_diff.path)

        for git_diff in template_changes["modified_files"]:
            upsert_template_paths.append(git_diff.path)

        for git_diff in template_changes["deleted_files"]:
            deleted_template_paths.append(git_diff.path)

        try:
            iambic_config = await load_iambic_config(repo_dir)
        except ValueError as err:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "repo": repo.repo_name,
                    "tenant": tenant.name,
                    "error": str(err),
                }
            )
            continue

        if create_template_paths:
            await create_tenant_templates_and_definitions(
                tenant,
                iambic_config,
                repo,
                repo_dir,
                provider_definition_map,
                create_template_paths,
            )
        if upsert_template_paths:
            await upsert_tenant_templates_and_definitions(
                tenant,
                iambic_config,
                repo,
                repo_dir,
                provider_definition_map,
                upsert_template_paths,
            )
        if deleted_template_paths:
            await delete_tenant_templates_and_definitions(
                tenant,
                repo,
                repo_dir,
                deleted_template_paths,
            )

    tenant.iambic_templates_last_parsed = iambic_templates_last_parsed
    await tenant.write()
