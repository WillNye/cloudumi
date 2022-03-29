import ruamel.yaml as yaml
from asgiref.sync import async_to_sync

from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.lib.dynamo import RestrictedDynamoHandler
from common.models import SpokeAccount

LOG = config.get_logger()


@app.task
def synchronize_account_ids_to_name(context: dict) -> bool:
    LOG.info("Synchronizing account id-name aliases")
    host = context.get("host")
    static_config = config.get_tenant_static_config_from_dynamo(host)
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", host).list
    static_config["account_ids_to_name"] = {
        x: y for d in spoke_accounts for x, y in d.items()
    }
    ddb = RestrictedDynamoHandler()
    async_to_sync(ddb.update_static_config_for_host)(
        yaml.dump(static_config), "celery worker", host
    )
    return True
