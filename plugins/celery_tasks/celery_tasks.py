"""
This module controls defines internal-only celery tasks and their applicable schedules. These will be combined with
the external tasks

"""
from datetime import timedelta
from typing import Any

from common.celery_tasks.celery_tasks import get_celery_app
from common.config import config
from common.lib.timeout import Timeout

region = config.region

app = get_celery_app()

broker_transport_options = config.get("_global_.celery.broker_transport_options")
if broker_transport_options:
    app.conf.update({"broker_transport_options": dict(broker_transport_options)})

app.conf.result_expires = config.get("_global_.celery.result_expires", 60)
app.conf.worker_prefetch_multiplier = config.get(
    "_global_.celery.worker_prefetch_multiplier", 4
)
app.conf.task_acks_late = config.get("_global_.celery.task_acks_late", True)

if config.get("_global_.celery.purge"):
    # Useful to clear celery queue in development
    with Timeout(seconds=5, error_message="Timeout: Are you sure Redis is running?"):
        app.control.purge()


schedule = timedelta(seconds=1800)

internal_schedule: dict[str, Any] = {}


def init():
    """Initialize the Celery Tasks plugin."""
    return internal_schedule
