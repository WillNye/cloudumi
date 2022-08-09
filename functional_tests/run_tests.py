# content of myinvoke.py
import pytest
from pytest import ErrorCode
import sys
from util.log import logger


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    logger.info("Running functional tests")
    if pytest.main(["-qq"], plugins=[MyPlugin()]) in [ErrorCode.TESTS_FAILED, ErrorCode.USAGE_ERROR]:
        raise RuntimeError(f"Functional tests failed")
