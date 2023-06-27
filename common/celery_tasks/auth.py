from asgiref.sync import async_to_sync

from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml
from common.models import SpokeAccount

LOG = config.get_logger(__name__)


@app.task
def synchronize_account_ids_to_name(context: dict) -> bool:
    LOG.info("Synchronizing account id-name aliases")
    tenant = context.get("tenant")
    static_config = config.get_tenant_static_config_from_dynamo(tenant)
    spoke_accounts = (
        ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).list
    )
    static_config["account_ids_to_name"] = {
        y.get("account_id"): y.get("name") for y in spoke_accounts
    }
    ddb = RestrictedDynamoHandler()
    async_to_sync(ddb.update_static_config_for_tenant)(
        yaml.dump(static_config), "celery worker", tenant
    )
    return True
