import logging

import celery

import plugins
from common.celery_tasks import celery_tasks
from util.log import logger

if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    celery_tasks.app.worker_main(["worker", "--loglevel=DEBUG"])
