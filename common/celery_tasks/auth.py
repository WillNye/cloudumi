from common.celery_tasks.celery_tasks import app
from common.config import config
from common.config.models import ModelAdapter
from common.models import SpokeAccount

LOG = config.get_logger()


@app.task
def synchronize_account_ids_to_name(context: dict) -> bool:
    LOG.info("Synchronizing account id-name aliases")
    host = context.get("host")
    static_config = config.get_tenant_static_config_from_dynamo(host)
    spoke_accounts = ModelAdapter(SpokeAccount).load_config("spoke_accounts", host).dict
    static_config["account_ids_to_name"] = {x: y for x, y in spoke_accounts.items()}
    config.update_tenant_static_config_in_dynamo(host, static_config)
    return True
