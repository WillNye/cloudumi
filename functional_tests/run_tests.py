# content of myinvoke.py
import argparse
import os
import pathlib

# import gevent
import pytest

# from locust import events
# from locust.env import Environment
# from locust.stats import stats_history, stats_printer
from pytest import ExitCode

from common.config import config

# from load_tests.locustfile import LoadTest

# locust_env = Environment(user_classes=[LoadTest], events=events)

logger = config.get_logger()

parser = argparse.ArgumentParser(description="Stage")
parser.add_argument(
    "--stage",
    help="Stage of deployment. Functional tests run in staging and prod",
)

parser.add_argument("--loc", help="Location of functional tests")
args = parser.parse_args()
stage = args.stage
loc = args.loc

if stage is None:
    stage = os.getenv("STAGE")
if loc is None:
    loc = pathlib.Path(__file__).parent.absolute()


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    if stage and loc and stage in ["staging", "prod2"]:
        logger.info("Running functional tests")
        conftest = __import__("functional_tests.conftest")

        if pytest.main(
            # ["-s", "-k", "test_api_v4_role_access", loc],
            # ["-s", "-k", "test_celery", loc],
            ["-s", loc],
            plugins=[conftest, MyPlugin()],
        ) in [
            ExitCode.TESTS_FAILED,
            ExitCode.USAGE_ERROR,
        ]:
            raise RuntimeError("Functional tests failed")

        # runner = locust_env.create_local_runner()
        # locust_env.events.init.fire(environment=locust_env, runner=runner)
        # gevent.spawn(stats_printer(locust_env.stats))
        # gevent.spawn(stats_history, locust_env.runner)
        # runner.start(2, spawn_rate=0.25)
        # gevent.spawn_later(60, lambda: runner.quit())
        # runner.greenlet.join()


if __name__ == "__main__":
    run()
