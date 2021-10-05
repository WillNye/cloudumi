"""
This module controls defines internal-only celery tasks and their applicable schedules. These will be combined with
the external tasks

"""
import json
import os
from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import Celery

from cloudumi_common.config import config
from cloudumi_common.lib.json_encoder import SetEncoder
from cloudumi_common.lib.redis import RedisHandler
from cloudumi_common.lib.timeout import Timeout

region = config.region

app = Celery(
    "tasks",
    broker=config.get(
        f"celery.broker.{config.region}",
        config.get("_global_.celery.broker.global", "redis://127.0.0.1:6379/1"),
    ),
    backend=config.get(
        f"celery.backend.{config.region}",
        config.get("_global_.celery.broker.global", "redis://127.0.0.1:6379/2"),
    ),
)

if config.get(f"_global_.redis.use_redislite"):
    import tempfile

    import redislite

    redislite_db_path = os.path.join(
        config.get(f"_global_.redis.redislite.db_path", tempfile.NamedTemporaryFile().name)
    )
    redislite_client = redislite.Redis(redislite_db_path)
    redislite_socket_path = f"redis+socket://{redislite_client.socket_file}"
    app = Celery(
        "tasks",
        broker=f"{redislite_socket_path}?virtual_host=1",
        backend=f"{redislite_socket_path}?virtual_host=2",
    )

app.conf.result_expires = config.get(f"_global_.celery.result_expires", 60)
app.conf.worker_prefetch_multiplier = config.get(f"_global_.celery.worker_prefetch_multiplier", 4)
app.conf.task_acks_late = config.get(f"_global_.celery.task_acks_late", True)

if config.get(f"_global_.celery.purge") and not config.get(f"_global_.redis.use_redislite"):
    # Useful to clear celery queue in development
    with Timeout(seconds=5, error_message="Timeout: Are you sure Redis is running?"):
        app.control.purge()


@app.task(soft_time_limit=600)
def cache_application_information(host):
    """
    This task retrieves application information from configuration. You may want to override this function to
    utilize your organization's CI/CD pipeline for this information.
    :return:
    """
    apps_to_roles = {}
    for k, v in config.get(f"site_configs.{host}.application_settings", {}).items():
        apps_to_roles[k] = v.get("roles", [])

    red = RedisHandler().redis_sync(host)
    red.set(
        config.get(f"site_configs.{host}.celery.apps_to_roles.redis_key", f"{host}_APPS_TO_ROLES"),
        json.dumps(apps_to_roles, cls=SetEncoder),
    )


@app.task
def generate_consoleme_saas_configuration():
    """
    This task combines all customer configurations into a single configuration for consoleme saas, segmented by
    customer. If last known configuration for customer is invalid, we make noise, and load the one we can find that is
    valid.
    # _ configs are first, followed in alphabetical order by org
    :return:
    """
    # TODO
    pass


schedule = timedelta(seconds=1800)

internal_schedule = {
    "generate_consoleme_saas_configuration": {
        "task": "cloudumi_plugins.plugins.celery_tasks.generate_consoleme_saas_configuration",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
    "cache_application_information": {
        "task": "cloudumi_plugins.plugins.celery_tasks.celery_tasks.cache_application_information",
        "options": {"expires": 4000},
        "schedule": schedule,
    },
}


def init():
    """Initialize the Celery Tasks plugin."""
    return internal_schedule
