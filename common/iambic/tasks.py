from common.aws.role_access.celery_tasks import sync_all_iambic_data_for_tenant
from common.iambic.config.utils import update_tenant_providers_and_definitions
from common.iambic.templates.tasks import sync_tenant_templates_and_definitions
from common.request_types.tasks import upsert_tenant_request_types


async def run_all_iambic_tasks_for_tenant(tenant_name: str):
    """This function will run all tasks related to updating IAMbic data for a tenant.

    Included:
    - Pulling main or cloning the repo if it isn't on disk
    - Syncing IAMbic templates either a full sync or a diff from a point in time
    - Running the legacy caching sync to populate AWS specific models
    - Updating the tenants IAMbic providers like AWS, Azure, etc.
    - Updating the tenants IAMbic provider definitions like AWS accounts and orgs
    - Upserting default request types for the tenant
        - Also includes upserting
            - Change Types
            - Change Templates
            - Change Fields
    """
    await sync_tenant_templates_and_definitions(tenant_name)
    await sync_all_iambic_data_for_tenant(tenant_name)
    await update_tenant_providers_and_definitions(tenant_name)
    await upsert_tenant_request_types(tenant_name)
