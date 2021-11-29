import logging
import celery
from cloudumi_common.celery_tasks import celery_tasks

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    celery_tasks()
