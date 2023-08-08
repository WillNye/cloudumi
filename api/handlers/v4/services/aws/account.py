from common.celery_tasks.celery_tasks import app as celery_app
from common.config.models import ModelAdapter
from common.handlers.base import BaseAdminHandler
from common.models import OrgAccount


class OrgAccountBackgroundTasksHandler(BaseAdminHandler):
    async def get(self):
        org_account: OrgAccount = (
            ModelAdapter(OrgAccount)
            .load_config("org_accounts", self.ctx.tenant)
            .models[0]
        )  # type: ignore

        self.write(
            {
                "data": dict(
                    accounts_excluded_from_automatic_onboard=org_account.accounts_excluded_from_automatic_onboard,
                    last_updated_accounts_excluded_automatic_onboard=org_account.last_updated_accounts_excluded_automatic_onboard,
                )
            }
        )

        self.set_status(200)
        self.finish()

    async def put(self):
        tenant = self.ctx.tenant

        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_organization_structure",
            kwargs={"tenant": tenant, "force": True},
        )

        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_scps_across_organizations",
            kwargs={"tenant": tenant},
            countdown=120,
        )

        self.write({"message": "Background tasks started"})
        self.set_status(200)
        self.finish()
