from common.handlers.base import BaseHandler
from common.lib.asyncio import aio_wrapper
from common.lib.auth import is_tenant_admin


class TasksHandler(BaseHandler):
    async def get(self):
        tenant = self.ctx.tenant
        if not is_tenant_admin(self.user, self.groups, tenant):
            # TODO: Log here
            self.set_status(403)
            await self.finish()
            return
        from common.celery_tasks.celery_tasks import app as celery_app

        # TODO: should show last time tasks were run
        # TODO: These tasks are slow. We should cache these results
        celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.cache_credential_authorization_mapping",
            kwargs={"tenant": tenant},
        )
        active = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"tenant": tenant, "status": "active"},
        )
        scheduled = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"tenant": tenant, "status": "scheduled"},
        )
        revoked = celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.get_current_celery_tasks",
            kwargs={"tenant": tenant, "status": "revoked"},
        )
        self.write(
            {
                "active": await aio_wrapper(active.get),
                "scheduled": await aio_wrapper(scheduled.get),
                "revoked": await aio_wrapper(revoked.get),
            }
        )

    async def post(self):
        tenant = self.ctx.tenant
        if not is_tenant_admin(self.user, self.groups, tenant):
            # TODO: Log here
            self.set_status(403)
            await self.finish()
            return
        # from common.celery_tasks.celery_tasks import app as celery_app
