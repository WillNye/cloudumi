from common.celery_tasks.celery_tasks import app as celery_app
from common.handlers.base import BaseAdminHandler
from common.models import Status2, WebResponse


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

        self.write(
            WebResponse(
                message="Background tasks started",
                status=Status2.success,
                status_code=200,
                data=None,
                reason=None,
            ).json(exclude_unset=True)
        )
        self.set_status(200)
        self.finish()
