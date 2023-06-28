from common.aws.role_access.celery_tasks import sync_all_iambic_data_for_tenant
from common.iambic.config.utils import update_tenant_providers_and_definitions
from common.iambic.templates.tasks import sync_tenant_templates_and_definitions
from common.request_types.tasks import upsert_tenant_request_types


async def run_all_iambic_tasks_for_tenant(tenant_name: str):
    await sync_tenant_templates_and_definitions(tenant_name)
    await sync_all_iambic_data_for_tenant(tenant_name)
    await update_tenant_providers_and_definitions(tenant_name)
    await upsert_tenant_request_types(tenant_name)
