import asyncio
import sys
from collections import defaultdict
from datetime import datetime
from itertools import chain
from typing import Optional, Type, Union

import pytz
from git import Repo
from iambic.core.models import BaseTemplate as IambicBaseTemplate
from sqlalchemy import and_, cast, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from common.aws.utils import get_resource_arn
from common.config import config as saas_config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import (
    TRUSTED_PROVIDER_RESOLVER_MAP,
    TenantProviderDefinition,
    TrustedProvider,
)
from common.iambic.config.utils import (
    list_tenant_provider_definitions,
    update_tenant_providers_and_definitions,
)
from common.iambic.git.models import IambicRepo
from common.iambic.interface import IambicConfigInterface
from common.iambic.templates.models import (
    IambicTemplate,
    IambicTemplateContent,
    IambicTemplateProviderDefinition,
)
from common.iambic.templates.utils import get_template_str_value_for_provider_definition
from common.lib.asyncio import NoqSemaphore
from common.pg_core.utils import bulk_add, bulk_delete
from common.tenants.models import Tenant

log = saas_config.get_logger(__name__)


async def create_tenant_templates_and_definitions(
    tenant: Tenant,
    iambic_config_interface: IambicConfigInterface,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    template_paths: Optional[list[str]] = None,
):
    """
    Create templates and template provider definitions for a tenant.

    Args:
        tenant (Tenant): The Tenant object for which templates and definitions are to be created.
        iambic_config_interface: The class used to interface with the tenant repo's IAMbic config instance.
        provider_definition_map (dict[dict[str, TenantProviderDefinition]]): A map of provider definitions.
        template_paths (list[str], optional): A list of template paths. Defaults to None.
    """
    template_type_provider_map = {}
    iambic_templates = []
    iambic_template_content_list = []
    iambic_template_provider_definitions = []
    is_full_create = not bool(template_paths)
    iambic_config = await iambic_config_interface.get_iambic_config()
    repo_name = iambic_config_interface.iambic_repo.repo_name
    repo_dir = iambic_config_interface.iambic_repo.file_path
    tenant_id = int(tenant.id)
    tenant_name = tenant.name

    # If no template paths provided, gather all templates from the repository directory
    if not template_paths:
        template_paths = await iambic_config_interface.gather_templates()

    log.info(
        {
            "message": "Creating templates",
            "tenant": tenant_name,
            "template_count": len(template_paths),
            "repo": repo_name,
        }
    )

    # Collect provider definitions from the template repo
    for raw_iambic_template in await iambic_config_interface.load_templates(
        template_paths, iambic_config.template_map
    ):
        provider = template_type_provider_map.get(raw_iambic_template.template_type)

        # If provider not already mapped, find and map the provider
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
                    "repo": repo_name,
                    "tenant": tenant_name,
                    "template_type": raw_iambic_template.template_type,
                    "error": "Could not find provider for template type.",
                }
            )
            continue

        # Create a new IambicTemplate instance and append to list
        file_path = str(raw_iambic_template.file_path).replace(repo_dir, "")
        if file_path.startswith("/"):
            file_path = file_path[1:]
        iambic_template = IambicTemplate(
            tenant=tenant,
            repo_name=repo_name,
            file_path=file_path,
            template_type=raw_iambic_template.template_type,
            provider=provider,
            resource_type=raw_iambic_template.resource_type,
            resource_id=raw_iambic_template.resource_id,
        )
        iambic_templates.append(iambic_template)

        # Create a new IambicTemplateContent instance and append to list
        iambic_template_content = IambicTemplateContent(
            tenant=tenant,
            iambic_template=iambic_template,
            content=raw_iambic_template.dict(exclude_unset=False),
        )
        iambic_template_content_list.append(iambic_template_content)

        provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP.get(provider)
        if provider_resolver.provider_defined_in_template:
            # Provider definition can be resolved from the template itself
            # Use the provider resolver to get the provider definition name from the template
            pd_name = provider_resolver.get_name_from_iambic_template(
                raw_iambic_template
            )
            # Get the tenant provider definition instance using the provider definition name
            tpd = provider_definition_map[provider].get(pd_name)
            iambic_template_provider_definitions.append(
                IambicTemplateProviderDefinition(
                    tenant=tenant,
                    iambic_template=iambic_template,
                    resource_id=raw_iambic_template.resource_id,
                    tenant_provider_definition=tpd,
                )
            )
        else:
            # The provider definition is defined via rules in the template
            # Iterate each provider definition in the config and check the template resource is on the provider
            provider_defs = provider_resolver.get_provider_definitions_from_config(
                iambic_config
            )
            for provider_def in provider_defs:
                if iambic_config_interface.evaluate_on_provider(
                    raw_iambic_template, provider_def
                ):
                    pd_name = provider_resolver.get_name_from_iambic_provider_config(
                        provider_def
                    )
                    # Get the tenant provider definition instance using the provider definition name
                    tpd = provider_definition_map[provider].get(pd_name)
                    if not tpd:
                        log.error(
                            "Could not find provider definition for template provider definition.",
                            provider_def=provider_def,
                            pd_name=pd_name,
                            tpd=tpd,
                            provider_defs=provider_defs,
                        )
                        continue

                    secondary_resource_id = None
                    if provider == "aws":
                        secondary_resource_id = await get_resource_arn(
                            tpd, raw_iambic_template
                        )
                    iambic_template_provider_definitions.append(
                        IambicTemplateProviderDefinition(
                            tenant=tenant,
                            iambic_template=iambic_template,
                            tenant_provider_definition=tpd,
                            secondary_resource_id=secondary_resource_id,
                            resource_id=get_template_str_value_for_provider_definition(
                                raw_iambic_template.resource_id, provider_def
                            ),
                        )
                    )

    try:
        if iambic_templates:
            await bulk_add(iambic_templates)
    except IntegrityError:
        if is_full_create:
            # Rollback everything and try again if the tenant is new
            await rollback_full_create(tenant_id)
        else:
            # Desync has occurred and needs to be remediated
            # This is a fallback where we delete the templates that shouldn't exist and try again
            async with ASYNC_PG_SESSION() as session:
                stmt = (
                    select(IambicTemplate)
                    .filter(
                        IambicTemplate.tenant_id == tenant_id,
                        IambicTemplate.repo_name == repo_name,
                        IambicTemplate.file_path.in_(
                            [t.file_path for t in iambic_templates]
                        ),
                    )
                    .join(
                        IambicTemplateContent,
                        IambicTemplateContent.iambic_template_id == IambicTemplate.id,
                    )
                    .join(
                        IambicTemplateProviderDefinition,
                        IambicTemplateProviderDefinition.iambic_template_id
                        == IambicTemplate.id,
                    )
                    .options(
                        contains_eager(IambicTemplate.content),
                        contains_eager(IambicTemplate.provider_definition_refs),
                    )
                )
                items = await session.execute(stmt)
                existing_templates = items.scalars().unique().all()

            log.warning(
                "Removing de-synced templates and trying again.",
                tenant=tenant_name,
                repo=repo_name,
                templates=[t.file_path for t in existing_templates],
            )

            # Deletes templates, their content, and their definitions
            await bulk_delete(existing_templates, False)

        if iambic_templates:
            await bulk_add(iambic_templates)

    if iambic_template_content_list:
        await bulk_add(iambic_template_content_list)
    if iambic_template_provider_definitions:
        await bulk_add(iambic_template_provider_definitions)


async def update_tenant_template(
    tenant: Tenant,
    iambic_config_interface: IambicConfigInterface,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    raw_iambic_template: Type[IambicBaseTemplate],
    provider: TrustedProvider,
) -> tuple[Union[str, None], list[IambicTemplateProviderDefinition]]:
    """
    Updates a single tenant template

    Args:
        tenant (Tenant): The Tenant object for which templates and definitions are to be created.
        iambic_config_interface: The class used to interface with the tenant repo's IAMbic config instance.
        provider_definition_map (dict[dict[str, TenantProviderDefinition]]): A map of provider definitions.
        raw_iambic_template (IambicTemplate): The IAMbic template to be updated.
        provider (TrustedProvider): The raw_iambic_template's provider TrustedProvider instance.

    Returns: tuple with 2 elements that are an XOR.
        The first element is the template's file path which is used if the template is not in the DB
        The second element is a list of IambicTemplateProviderDefinition instances to be created
    """
    iambic_template_provider_definitions = []
    iambic_config = await iambic_config_interface.get_iambic_config()
    repo_name = iambic_config_interface.iambic_repo.repo_name
    repo_dir = iambic_config_interface.iambic_repo.file_path

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
                    IambicTemplate.repo_name == repo_name,
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
    if file_path.startswith("/"):
        file_path = file_path[1:]
    if iambic_template.file_path != file_path:
        iambic_template.file_path = file_path
        await iambic_template.write()

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                update(IambicTemplateContent)
                .where(
                    and_(
                        IambicTemplateContent.iambic_template_id == iambic_template.id,
                        IambicTemplateContent.tenant_id == tenant.id,
                    )
                )
                .values(content=raw_iambic_template.dict(exclude_unset=False))
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
        # Currently no support of secondary resource id here
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
                    resource_id=raw_iambic_template.resource_id,
                )
            )
    else:
        provider_defs = provider_resolver.get_provider_definitions_from_config(
            iambic_config
        )
        for provider_def in provider_defs:
            if iambic_config_interface.evaluate_on_provider(
                raw_iambic_template, provider_def, False
            ):
                pd_name = provider_resolver.get_name_from_iambic_provider_config(
                    provider_def
                )
                tpd = provider_definition_map[provider].get(pd_name)
                if tpd.id in existing_provider_definition_id_map:
                    if provider == "aws":
                        secondary_resource_id = await get_resource_arn(
                            tpd, raw_iambic_template
                        )
                        if tpd.secondary_resource_id != secondary_resource_id:
                            # Secondary resource id is out of sync
                            # This is most likely due to a change in the resource path
                            tpd.secondary_resource_id = secondary_resource_id
                            await tpd.write()

                    # The reference already exists and is in the template so skip it
                    existing_provider_definition_id_map.pop(tpd.id, None)
                else:
                    secondary_resource_id = None
                    if provider == "aws":
                        secondary_resource_id = await get_resource_arn(
                            tpd, raw_iambic_template
                        )
                    iambic_template_provider_definitions.append(
                        IambicTemplateProviderDefinition(
                            tenant_id=tenant.id,
                            iambic_template_id=iambic_template.id,
                            tenant_provider_definition_id=tpd.id,
                            secondary_resource_id=secondary_resource_id,
                            resource_id=get_template_str_value_for_provider_definition(
                                raw_iambic_template.resource_id, provider_def
                            ),
                        )
                    )

    # Remove any template provider definitions that were not evaluated using the template
    if existing_provider_definition_id_map:
        await bulk_delete(list(existing_provider_definition_id_map.values()))

    return None, iambic_template_provider_definitions


async def upsert_tenant_templates_and_definitions(
    tenant: Tenant,
    iambic_config_interface: IambicConfigInterface,
    provider_definition_map: dict[dict[str, TenantProviderDefinition]],
    template_paths: list[str],
):
    """
    Creates and updates templates and template provider definitions for a tenant.

    It works by processing the provided template paths in a semaphore that calls the update_tenant_template.
    This function then handles response from update_tenant_template by
        Creating templates that don't exist by calling create_tenant_templates_and_definitions
        Creating template provider definitions for templates that do exist with missing definitions

    Args:
        tenant (Tenant): The Tenant object for which templates and definitions are to be created.
        iambic_config_interface: The class used to interface with the tenant repo's IAMbic config instance.
        provider_definition_map (dict[dict[str, TenantProviderDefinition]]): A map of provider definitions.
        template_paths (list[str], optional): A list of template paths. Defaults to None.
    """
    template_type_provider_map = {}
    update_tenant_template_semaphore = NoqSemaphore(update_tenant_template, 30)
    repo_name = iambic_config_interface.iambic_repo.repo_name

    log.info(
        {
            "message": "Updating templates",
            "tenant": tenant.name,
            "template_count": len(template_paths),
            "repo": repo_name,
        }
    )

    # Collect provider definitions from the template repo
    messages = []
    for raw_iambic_template in await iambic_config_interface.load_templates(
        template_paths
    ):
        provider = template_type_provider_map.get(raw_iambic_template.template_type)

        # If provider not already mapped, find and map the provider
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
                    "repo": repo_name,
                    "tenant": tenant.name,
                    "template_type": raw_iambic_template.template_type,
                    "error": "Could not find provider for template type.",
                }
            )
            continue

        messages.append(
            {
                "tenant": tenant,
                "iambic_config_interface": iambic_config_interface,
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
                iambic_config_interface,
                provider_definition_map,
                new_template_paths,
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
    iambic_config_interface: IambicConfigInterface,
    template_paths: list[str],
):
    """
    Removes deleted templates from the DB in chunks

    Args:
        tenant (Tenant): The Tenant object for which templates and definitions are to be created.
        iambic_config_interface: The class used to interface with the tenant repo's IAMbic config instance.
        template_paths (list[str], optional): A list of template paths. Defaults to None.
    """
    repo_name = iambic_config_interface.iambic_repo.repo_name
    repo_dir = iambic_config_interface.iambic_repo.file_path
    log.info(
        {
            "message": "Deleting templates",
            "tenant": tenant.name,
            "template_count": len(template_paths),
            "repo": repo_name,
        }
    )

    deleted_template_paths = []
    for template_path in template_paths:
        template_path = str(template_path).replace(repo_dir, "")
        if template_path.startswith("/"):
            template_path = template_path[1:]
        deleted_template_paths.append(template_path)

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
                            IambicTemplate.repo_name == repo_name,
                            IambicTemplate.file_path.in_(path_chunk),
                        )
                    )
                    await session.execute(stmt)
                    await session.flush()


async def full_create_tenant_templates_and_definitions(
    tenant: Tenant, provider_definition_map: dict[dict[str, TenantProviderDefinition]]
):
    """
    Creates the templates and template provider definitions for a tenant.

    Only used if the tenant is new and is determined by checking Tenant.iambic_templates_last_parsed

    Args:
        tenant (Tenant): The Tenant object for which templates and definitions are to be created.
        provider_definition_map (dict[dict[str, TenantProviderDefinition]]): A map of provider definitions.
    """
    iambic_repos = await IambicRepo.get_all_tenant_repos(str(tenant.name))

    # Iterate the tenants iambic repos
    for iambic_repo in iambic_repos:
        # Create the templates and definitions
        await create_tenant_templates_and_definitions(
            tenant,
            IambicConfigInterface(iambic_repo),
            provider_definition_map,
        )


async def rollback_full_create(tenant_id: int):
    """Deletes all template data for a tenant in the event of a failure on create.

    Args:
        tenant (Tenant): The tenant object for which templates and definitions are to be deleted.
    """
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            # TODO : Fix
            stmt = delete(IambicTemplateContent).where(
                IambicTemplateContent.tenant_id == tenant_id
            )
            await session.execute(stmt)
            await session.flush()

            stmt = delete(IambicTemplateProviderDefinition).where(
                IambicTemplateProviderDefinition.tenant_id == tenant_id
            )
            await session.execute(stmt)
            await session.flush()

            stmt = delete(IambicTemplate).where(IambicTemplate.tenant_id == tenant_id)
            await session.execute(stmt)
            await session.flush()


async def sync_tenant_templates_and_definitions(tenant_name: str):
    """
    Sync the IAMbic templates and template provider definitions for a tenant.

    Args:
        tenant_name (str): The name of the tenant.
    """
    tenant = await Tenant.get_by_name(tenant_name)
    if not tenant:
        log.error("Not a valid tenant", tenant=tenant_name)
        return
    iambic_repos = await IambicRepo.get_all_tenant_repos(tenant.name)
    if not iambic_repos:
        log.error(
            {
                "message": "No valid IAMbic repos found for tenant",
                "tenant": tenant.name,
            }
        )
        tenant.supported_template_types = []
        tenant.iambic_templates_last_parsed = None
        await tenant.write()
        await rollback_full_create(tenant.id)
        return
    elif len(iambic_repos) > 1:
        log.warning(
            {
                "message": "More than 1 Iambic Template repo has been configured. "
                "This will result in data being truncated in the cached template bucket.",
                "tenant": tenant.name,
            }
        )

    for iambic_repo in iambic_repos:
        await iambic_repo.clone_or_pull_git_repo()

    # TODO: Remove this legacy caching call
    iambic_repo = iambic_repos[0]
    iambic_config = IambicConfigInterface(iambic_repo)
    await iambic_config.cache_aws_templates()

    iambic_templates_last_parsed = tenant.iambic_templates_last_parsed
    if iambic_templates_last_parsed:
        iambic_templates_last_parsed = pytz.UTC.localize(iambic_templates_last_parsed)
    # Written up here to prevent request spamming causing multiple full creates
    tenant.iambic_templates_last_parsed = datetime.utcnow()
    await tenant.write()
    tenant_name = tenant.name
    tenant_id = tenant.id
    provider_definition_map = defaultdict(dict)

    # Populate the provider definition map where
    # k1 is the provider name, k2 is the provider definition str repr and the value is the provider definition
    raw_existing_definitions = await list_tenant_provider_definitions(tenant_id)
    if not raw_existing_definitions:
        await update_tenant_providers_and_definitions(tenant_name)
        raw_existing_definitions = await list_tenant_provider_definitions(tenant_id)
    if not raw_existing_definitions:
        log.error(
            "No provider definitions found for tenant",
            tenant=tenant_name,
        )
        return
    for existing_definition in raw_existing_definitions:
        provider_definition_map[existing_definition.provider][
            existing_definition.name
        ] = existing_definition

    # New tenant so perform a full create
    if not iambic_templates_last_parsed:
        try:
            await full_create_tenant_templates_and_definitions(
                tenant, provider_definition_map
            )
        except Exception as err:
            tenant.iambic_templates_last_parsed = None
            await tenant.write()
            await rollback_full_create(tenant.id)
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Unable to create tenant templates and definitions.",
                    "tenant": tenant_name,
                    "error": str(err),
                },
                exc_info=True,
            )
            raise
        return

    # Iterate the tenants iambic repos
    for repo in iambic_repos:
        iambic_config_interface = IambicConfigInterface(repo)
        repo_dir = repo.file_path
        # Get all changes since last parsed
        git_repo = Repo(repo_dir)
        from_sha = None
        to_sha = None
        for commit in git_repo.iter_commits("main"):  # Correctly resolve default branch
            if commit.committed_datetime < iambic_templates_last_parsed:
                break

            if not to_sha:
                to_sha = commit.hexsha
            else:
                from_sha = commit.hexsha

        template_changes = await iambic_config_interface.retrieve_git_changes(
            from_sha=from_sha, to_sha=to_sha
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
            if create_template_paths:
                await create_tenant_templates_and_definitions(
                    tenant,
                    iambic_config_interface,
                    provider_definition_map,
                    create_template_paths,
                )
            if upsert_template_paths:
                await upsert_tenant_templates_and_definitions(
                    tenant,
                    iambic_config_interface,
                    provider_definition_map,
                    upsert_template_paths,
                )
            if deleted_template_paths:
                await delete_tenant_templates_and_definitions(
                    tenant,
                    iambic_config_interface,
                    deleted_template_paths,
                )
        except Exception as err:
            tenant.iambic_templates_last_parsed = iambic_templates_last_parsed
            await tenant.write()
            await log.aerror(
                str(err),
                repo=repo.repo_name,
                tenant=tenant.name,
            )
            return
