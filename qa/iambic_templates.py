import json
from datetime import datetime, timedelta

from sqlalchemy import select, update

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.models import (
    IambicTemplate,
    IambicTemplateContent,
    IambicTemplateProviderDefinition,
)
from common.iambic.templates.tasks import (
    rollback_full_create,
    sync_tenant_templates_and_definitions,
)
from common.pg_core.utils import bulk_delete
from qa import TENANT_SUMMARY
from qa.utils import generic_api_get_request

"""Example script
import asyncio

from qa import setup, TENANT_NAME
asyncio.run(setup())

from qa.iambic_templates import list_templates_api_request, sync_test_tenant_templates, teardown_refs

# Repopulate the templates
await teardown_refs(TENANT_NAME)
await sync_test_tenant_templates()

# Attempt to get all IAM role templates from the API
list_templates_api_request("NOQ::AWS::IAM::Role")
"""


async def teardown_refs():
    """Will 'reset' the iambic templates for a tenant.

    Sets the last parsed date to None, and deletes all templates.
    This will result in a full reparse of all templates.
    """
    await rollback_full_create(TENANT_SUMMARY.tenant)


async def desync_on_full_create():
    """Used to check that the update functionality of the sync iambic templates function works.

    Sets the last parsed date to 16 weeks ago
    Deletes 50 templates
    Sets the content of every template to junk
    Removes every other template provider definition
    """
    tenant = TENANT_SUMMARY.tenant
    tenant.iambic_templates_last_parsed = None
    await tenant.write()

    # Attempt to perform full create with templates in the DB.
    # Expected behavior: All templates deleted
    await sync_test_tenant_templates()


async def force_change_resolution():
    """Used to check that the update functionality of the sync iambic templates function works.

    Sets the last parsed date to 16 weeks ago
    Deletes 50 templates
    Sets the content of every template to junk
    Removes every other template provider definition
    """
    tenant = TENANT_SUMMARY.tenant
    tenant.iambic_templates_last_parsed = datetime.utcnow() - timedelta(weeks=16)

    async with ASYNC_PG_SESSION() as session:
        items = await session.execute(
            select(IambicTemplate).where(IambicTemplate.tenant_id == tenant.id)
        )
        iambic_templates = items.scalars().all()

    await bulk_delete(iambic_templates[:50])

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = (
                update(IambicTemplateContent)
                .where(IambicTemplateContent.tenant_id == tenant.id)
                .values(content={"some": "junk"})
            )
            await session.execute(stmt)

    async with ASYNC_PG_SESSION() as session:
        items = await session.execute(select(IambicTemplateProviderDefinition))
        template_provider_def_refs = items.scalars().all()

    await bulk_delete(template_provider_def_refs[::2])


async def sync_test_tenant_templates():
    await sync_tenant_templates_and_definitions(TENANT_SUMMARY.tenant_name)


def list_templates_api_request(
    template_type: str = None,
    resource_id: str = None,
    page: int = 1,
    page_size: int = 50,
):
    params = {
        "template_type": template_type,
        "resource_id": resource_id,
        "page": page,
        "page_size": page_size,
    }
    response = generic_api_get_request(
        "v4/templates",
        params={k: v for k, v in params.items() if v is not None},
    )
    if not response.ok:
        print(response.text)
        response.raise_for_status()

    response = response.json()
    print(json.dumps(response, indent=2))
    return response
