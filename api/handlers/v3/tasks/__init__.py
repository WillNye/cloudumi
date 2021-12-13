from asgiref.sync import sync_to_async

from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all


class TasksHandler(BaseHandler):
    async def get(self):
        host = self.ctx.host
        if not can_admin_all(self.user, self.groups, host):
            # TODO: Log here
            self.set_status(403)
            await self.finish()
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        # TODO: should show last time tasks were run
        # TODO: These tasks are slow. We should cache these results
        celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            kwargs={"host": host},
        )
        active = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"host": host, "status": "active"},
        )
        scheduled = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"host": host, "status": "scheduled"},
        )
        revoked = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"host": host, "status": "revoked"},
        )
        self.write(
            {
                "active": await sync_to_async(active.get)(),
                "scheduled": await sync_to_async(scheduled.get)(),
                "revoked": await sync_to_async(revoked.get)(),
            }
        )

    async def post(self):
        host = self.ctx.host
        if not can_admin_all(self.user, self.groups, host):
            # TODO: Log here
            self.set_status(403)
            await self.finish()
            return
        # from common.celery_tasks.celery_tasks import app as celery_app
