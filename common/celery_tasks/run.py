import os

from common.celery_tasks import celery_tasks
from common.handlers.external_processes import kill_proc, launch_proc
from util.log import logger

if os.getenv("DEBUG"):
    os.system("systemctl start ssh")

if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    log_level = os.getenv("CELERY_LOG_LEVEL", "DEBUG")
    concurrency = os.getenv("CELERY_CONCURRENCY", "16") or "16"
    try:
        launch_proc(
            "fluent-bit",
            "/opt/fluent-bit/bin/fluent-bit -c /etc/fluent-bit/fluent-bit.conf",
        )
    except ValueError:
        logger.warning("Fluent-bit already running")
    celery_tasks.app.worker_main(
        [
            "worker",
            f"--loglevel={log_level}",
            "-B",
            "-E",
            f"--concurrency={concurrency}",
        ]
    )
    try:
        kill_proc("fluent-bit")
    except ValueError:
        logger.warning("Fluent-bit not running")
