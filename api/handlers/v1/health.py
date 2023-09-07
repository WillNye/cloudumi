"""Health handler."""
import tornado.web

from common.handlers.base import TornadoRequestHandler


class HealthHandler(TornadoRequestHandler):
    """Health handler."""

    async def get(self):
        """Healthcheck endpoint
        ---
        get:
            description: Healtcheck endpoint
            responses:
                200:
                    description: Simple endpoint that returns 200 and a string to signify that the server is up.
        """
        self.write("OK")
        if self.request.query_arguments.get("celery"):
            from common.celery_tasks.celery_tasks import app as celery_app

            celery_app.send_task(
                "common.celery_tasks.celery_tasks.healthcheck",
                kwargs={
                    k: v
                    for k, v in self.request.query_arguments.items()
                    if k != "tenant"
                },
            )


class HealthVanillaHandler(tornado.web.RequestHandler):
    """Health Vanilla handler."""

    async def get(self):
        """Healthcheck endpoint
        ---
        get:
            description: Healtcheck endpoint
            responses:
                200:
                    description: Simple endpoint that returns 200 and a string to signify that the server is up.
        """
        self.write("OK")
