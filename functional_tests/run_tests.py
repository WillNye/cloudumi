# content of myinvoke.py
import argparse
import os
import pathlib

import pytest
from pytest import ExitCode

from common.config import config

logger = config.get_logger()

parser = argparse.ArgumentParser(description="Stage")
parser.add_argument(
    "--stage",
    help="Stage of deployment. Functional tests only run in staging",
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
    if stage and loc and stage == "staging":
        logger.info("Running functional tests")
        conftest = __import__("functional_tests.conftest")
        if pytest.main([loc, "-k", "test_docs"], plugins=[conftest, MyPlugin()]) in [
            ExitCode.TESTS_FAILED,
            ExitCode.USAGE_ERROR,
        ]:
            raise RuntimeError("Functional tests failed")


if __name__ == "__main__":
    run()
