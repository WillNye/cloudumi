import argparse
import os
from multiprocessing import Process

from common.celery_tasks import celery_tasks
from common.config import config
from common.lib.plugins import fluent_bit

# from functional_tests import run_tests as functional_tests  ## TODO (see below)

logger = config.get_logger(__name__)

if os.getenv("DEBUG"):
    os.system("systemctl start ssh")

# functional_tests.run()  ## functional tests are only for API :( - TODO: make functional tests for both API and Celery


def start_worker(log_level, concurrency, queue_name=None, hostname=None, beat=None):
    args = [
        "worker",
        "-l",
        log_level,
        "-E",
        "--concurrency",
        str(concurrency),
        "--max-memory-per-child",
        "4000000",
        "--max-tasks-per-child",
        "50",
        "--soft-time-limit",
        "3600",
        "-O",
        "fair",
    ]
    if queue_name is not None:
        args.extend(["-Q", queue_name])
    if hostname is not None:
        args.extend(["-n", hostname])
    if beat is not None:
        args.extend(["-B"])
    celery_tasks.app.start(args)


def run_celery_worker(log_level: str = "DEBUG", concurrency: str = str(os.cpu_count())):

    # default worker
    p1 = Process(target=start_worker, args=(log_level, concurrency))
    p1.start()

    # high priority worker
    p2 = Process(
        target=start_worker,
        args=(log_level, concurrency, "high_priority", "high_priority@%h"),
    )
    p2.start()

    p1.join()
    p2.join()


def run_celery_test_worker(log_level: str = "DEBUG", concurrency: str = os.cpu_count()):
    """Like the run_celery_worker but with beat scheduler integrated for testing."""
    p1 = Process(target=run_celery_scheduler)
    p1.start()

    # default worker
    p2 = Process(target=start_worker, args=(log_level, concurrency))
    p2.start()

    # high priority worker
    p3 = Process(
        target=start_worker,
        args=(log_level, concurrency, "high_priority", "high_priority@%h"),
    )
    p3.start()

    p1.join()
    p2.join()
    p3.join()


def run_celery_scheduler(log_level: str = "DEBUG"):
    celery_tasks.app.start(f"beat -l {log_level}".split(" "))


def run_celery_flower(log_level: str = "DEBUG", port: int = 7101):
    celery_tasks.app.start(f"flower -l {log_level} --port={port}".split(" "))


def run_celery_inspect():
    celery_tasks.app.control.inspect().active()


def run_celery_events(log_level: str = "DEBUG"):
    celery_tasks.app.start(f"events -l {log_level}".split(" "))


if __name__ == "__main__":
    logger.info("Starting up celery tasks")
    log_level = os.getenv("CELERY_LOG_LEVEL", "DEBUG")
    concurrency = os.getenv("CELERY_CONCURRENCY", os.cpu_count())

    # Argument parsing
    parser = argparse.ArgumentParser(description="Process runtime profile.")
    parser.add_argument("--profile", dest="profile", help="runtime profile to be used")
    args = parser.parse_args()
    runtime_profile = (
        args.profile if args.profile else os.getenv("RUNTIME_PROFILE", "CELERY_WORKER")
    )

    fluent_bit.add_fluent_bit_service()

    match runtime_profile:
        case "CELERY_WORKER":
            run_celery_worker(log_level, concurrency)
        case "CELERY_WORKER_TEST":
            run_celery_test_worker(log_level, concurrency)
        case "CELERY_SCHEDULER":
            run_celery_scheduler(log_level)
        case "CELERY_FLOWER":
            run_celery_flower(log_level, port=7101)
        case "CELERY_INSPECT":
            run_celery_inspect()
        case "CELERY_EVENTS":
            run_celery_events(log_level)

    fluent_bit.remove_fluent_bit_service()
