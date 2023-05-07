# content of myinvoke.py
import argparse
import os
import pathlib
import tempfile

# import gevent
import pytest
import requests

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

# #alerts slack channel
SLACK_WEBHOOK_URL = (
    "A_SECRET"
)


def send_to_slack(message):
    payload = {"text": message}
    requests.post(SLACK_WEBHOOK_URL, json=payload)


def upload_to_transfer_sh(filepath):
    with open(filepath, "rb") as file:
        response = requests.put(
            f"https://transfer.sh/{os.path.basename(filepath)}",
            data=file,
        )
    return response.text


class MyPlugin:
    def pytest_sessionfinish(self):
        print("*** test run reporting finishing")


def run():
    if stage and loc and stage in ["staging", "prod2"]:
        logger.info("Running functional tests")
        conftest = __import__("functional_tests.conftest")

        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            prev_stdout = os.dup(1)
            os.dup2(output_file.fileno(), 1)
            exit_code = pytest.main(
                # ["--capture=sys", "-k", "TestCredentials", loc],
                ["--capture=sys", loc],
                plugins=[conftest, MyPlugin()],
            )

            # Restore the original stdout
            os.dup2(prev_stdout, 1)

            # Upload test output to transfer.sh and send to Slack
            output_file.flush()
            transfer_url = upload_to_transfer_sh(output_file.name)
            if exit_code in [ExitCode.TESTS_FAILED, ExitCode.USAGE_ERROR]:
                send_to_slack(
                    f"Functional tests failed. Check the logs for more information: {transfer_url}"
                )
                raise RuntimeError("Functional tests failed")
            else:
                send_to_slack(
                    f"Functional tests finished successfully. Test output: {transfer_url}"
                )


if __name__ == "__main__":
    run()
