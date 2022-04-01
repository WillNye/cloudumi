from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.celery_tasks.auth import synchronize_account_ids_to_name
from common.models import HubAccount, OrgAccount, SpokeAccount


class HubAccountConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = HubAccount
    _config_key = "hub_account"
    _identifying_keys = ["name"]


class SpokeAccountConfigurationCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = SpokeAccount
    _config_key = "spoke_accounts"
    _triggers = [synchronize_account_ids_to_name]
    _identifying_keys = ["name", "account_id"]


class OrgAccountConfigurationCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = OrgAccount
    _config_key = "org_accounts"
    _identifying_keys = ["org_id"]
