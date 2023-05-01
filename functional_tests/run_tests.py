# content of myinvoke.py
import argparse
import asyncio
import os
import pathlib
import subprocess

import pytest
from pytest import ExitCode

from common.config import config

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


def run_cypress_subprocess():
    return subprocess.run(
        ["npx", "cypress", "run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        cwd="ui",  # Set the working directory to 'ui'
    )


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


async def run_cypress_ui_tests():
    loop = asyncio.get_event_loop()
    if stage and loc and stage in ["staging", "prod2"]:
        logger.info("Running Cypress UI Functional tests")
        try:
            process = await loop.run_in_executor(
                None,
                lambda: subprocess.Popen(
                    ["cypress", "run"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    capture_output=True,
                    cwd="ui",
                    env=os.environ.copy(),
                ),
            )
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            if exit_code != 0:
                raise subprocess.CalledProcessError(exit_code, "Cypress tests failed")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return None, stdout, stderr
        except subprocess.CalledProcessError as e:
            print(f"Cypress tests failed with error code: {e.returncode}")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return e, stdout, stderr


if __name__ == "__main__":
    run()
