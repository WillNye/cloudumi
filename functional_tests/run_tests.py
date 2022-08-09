# content of myinvoke.py
import pytest
import sys


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    if pytest.main(["-qq"], plugins=[MyPlugin()]) in [ErrorCode.TESTS_FAILED, ErrorCode.USAGE_ERROR]:
        raise RuntimeError(f"Functional tests failed")
