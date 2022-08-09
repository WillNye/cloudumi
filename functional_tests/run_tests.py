# content of myinvoke.py
import pytest
from pytest import ExitCode

from util.log import logger


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    logger.info("Running functional tests")
    if pytest.main(["-qq"], plugins=[MyPlugin()]) in [
        ExitCode.TESTS_FAILED,
        ExitCode.USAGE_ERROR,
    ]:
        raise RuntimeError("Functional tests failed")
