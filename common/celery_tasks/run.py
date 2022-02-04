import os

from common.celery_tasks import celery_tasks
from util.log import logger

if os.getenv("DEBUG"):
    os.system("systemctl start ssh")

if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    log_level = os.getenv("CELERY_LOG_LEVEL", "DEBUG")
    concurrency = os.getenv("CELERY_CONCURRENCY", "16")
    celery_tasks.app.worker_main(
        ["worker", f"--loglevel={log_level}", "-B", f"--concurrency={concurrency}"]
    )
