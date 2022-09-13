from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.celery_tasks.celery_tasks import app as celery_app
from common.models import HubAccount, OrgAccount, SpokeAccount


class HubAccountConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = HubAccount
    _config_key = "hub_account"
    _identifying_keys = ["account_id"]


class SpokeAccountConfigurationCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = SpokeAccount
    _config_key = "spoke_accounts"
    _identifying_keys = ["account_id"]


class OrgAccountConfigurationCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = OrgAccount
    _config_key = "org_accounts"
    _identifying_keys = ["uuid"]

    async def _create(self, data):
        await super(OrgAccountConfigurationCrudHandler, self)._create(data)

        tenant = self.ctx.tenant
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_organization_structure",
            kwargs={"tenant": tenant},
        )
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_scps_across_organizations",
            kwargs={"tenant": tenant},
            countdown=120,
        )
