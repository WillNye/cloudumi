import asyncio
from typing import Union

from sqlalchemy import delete

from common import AWSAccount as SaaSAWSAccount
from common import (
    AwsIdentityRole,
    AWSRoleAccess,
    GitHubInstall,
    Request,
    RequestComment,
    TenantProvider,
    TenantProviderDefinition,
)
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.tasks import run_all_iambic_tasks_for_tenant
from common.request_types.utils import list_tenant_request_types
from qa import TENANT_SUMMARY
from qa.iambic_templates import teardown_refs
from qa.request_types import hard_delete_request_type


async def clear_iambic_install_refs() -> Union[str, None]:
    # Remove all template records
    await teardown_refs()
    tenant = TENANT_SUMMARY.tenant
    github_install = await GitHubInstall.get(tenant)
    github_install_id = github_install.installation_id if github_install else None
    if github_install_id:
        print(f"Deleting github install {github_install_id}")

    # Remove all request type records
    request_types = await list_tenant_request_types(tenant.id, exclude_deleted=False)
    await asyncio.gather(
        *[hard_delete_request_type(req_type) for req_type in request_types]
    )

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            # Remove all requests records
            await session.execute(delete(RequestComment))
            stmt = delete(Request).where(Request.tenant_id == tenant.id)
            await session.execute(stmt)

            # Remove AWS account and role access records
            stmt = delete(AWSRoleAccess).where(AWSRoleAccess.tenant_id == tenant.id)
            await session.execute(stmt)
            stmt = delete(AwsIdentityRole).where(AwsIdentityRole.tenant_id == tenant.id)
            await session.execute(stmt)
            stmt = delete(SaaSAWSAccount).where(SaaSAWSAccount.tenant_id == tenant.id)
            await session.execute(stmt)

            # Remove github installation id
            stmt = delete(GitHubInstall).where(GitHubInstall.tenant_id == tenant.id)
            await session.execute(stmt)

            # Remove provider and provider definitions
            stmt = delete(TenantProviderDefinition).where(
                TenantProviderDefinition.tenant_id == tenant.id
            )
            await session.execute(stmt)
            stmt = delete(TenantProvider).where(TenantProvider.tenant_id == tenant.id)
            await session.execute(stmt)

    return github_install_id


async def end_to_end_flow():
    # Each of these pieces should really be ran as steps so you can validate the state of the DB
    # This function is really here as a guide to how the steps should be ran
    github_install_id = await clear_iambic_install_refs()
    await run_all_iambic_tasks_for_tenant(TENANT_SUMMARY.tenant_name)
    # Nothing should be populated at this point because the repo hasn't been fully configured

    # Set installation id and re-run tasks
    # Now everything should be populated
    await GitHubInstall.create(TENANT_SUMMARY.tenant, github_install_id)
    await run_all_iambic_tasks_for_tenant(TENANT_SUMMARY.tenant_name)
