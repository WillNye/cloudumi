from common.celery_tasks.celery_tasks import app as celery_app
from common.handlers.base import BaseAdminHandler


class OrgAccountBackgroundTasksHandler(BaseAdminHandler):
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
