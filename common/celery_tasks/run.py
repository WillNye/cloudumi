import os

from common.celery_tasks import celery_tasks
from common.lib.plugins.fluent_bit import (
    add_fluent_bit_service,
    remove_fluent_bit_service,
)
from util.log import logger

if os.getenv("DEBUG"):
    os.system("systemctl start ssh")

if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    log_level = os.getenv("CELERY_LOG_LEVEL", "DEBUG")
    concurrency = os.getenv("CELERY_CONCURRENCY", "16") or "16"
    add_fluent_bit_service()
    celery_tasks.app.worker_main(
        [
            "worker",
            f"--loglevel={log_level}",
            "-B",
            "-E",
            f"--concurrency={concurrency}",
        ]
    )
    remove_fluent_bit_service()
