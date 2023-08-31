from common.iambic.templates.tasks import sync_tenant_templates_and_definitions
from common.request_types.tasks import upsert_tenant_request_types


async def run_all_iambic_tasks_for_tenant(tenant_name: str):
    """This function will run all tasks related to updating IAMbic data for a tenant.

    Any functions with a * are executed by a function called by this function.
    For example, sync_tenant_templates_and_definitions triggers sync_aws_role_access_for_tenant.

    Included:
    - Pulling main or cloning the repo if it isn't on disk
    - Syncing IAMbic templates either a full sync or a diff from a point in time
    - Updating the tenants IAMbic provider definitions like AWS accounts and orgs
    - Upserting default request types for the tenant
        - Also includes upserting
            - Change Types
            - Change Templates
            - Change Fields
    - *Running the legacy caching sync to populate AWS specific models
    - *Updating the tenants IAMbic providers like AWS, Azure, etc.
    """
    await sync_tenant_templates_and_definitions(tenant_name)
    await upsert_tenant_request_types(tenant_name)
