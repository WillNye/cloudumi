# content of myinvoke.py
import argparse
import sys

import pytest
from pytest import ExitCode

from util.log import logger

parser = argparse.ArgumentParser(description="Stage")
parser.add_argument(
    "--stage",
    help="Stage of deployment. Functional tests only run in staging",
)

parser.add_argument("--loc", help="Location of functional tests", default=".")
args = parser.parse_args()

if args.stage != "staging":
    sys.exit(0)


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    logger.info("Running functional tests")
    if pytest.main([args.loc], plugins=[MyPlugin()]) in [
        ExitCode.TESTS_FAILED,
        ExitCode.USAGE_ERROR,
    ]:
        raise RuntimeError("Functional tests failed")


if __name__ == "__main__":
    run()
