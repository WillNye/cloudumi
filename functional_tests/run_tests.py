import argparse
import os
import pathlib
import tempfile
from datetime import datetime

import boto3

# import gevent
import pytest
import requests
from botocore.config import Config
from botocore.exceptions import NoCredentialsError

# from locust import events
# from locust.env import Environment
# from locust.stats import stats_history, stats_printer
from pytest import ExitCode

from common.config import config

# from load_tests.locustfile import LoadTest

# locust_env = Environment(user_classes=[LoadTest], events=events)

logger = config.get_logger()
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

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


def generate_presigned_url(filepath):
    filename = os.path.basename(filepath)
    temp_files_bucket = config.get("_global_.s3_buckets.temp_files")
    bucket_path = f"{timestamp}-functional_tests"
    s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

    try:
        s3_client.upload_file(filepath, temp_files_bucket, f"{bucket_path}/{filename}")
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": temp_files_bucket,
                "Key": f"{bucket_path}/{filename}",
            },
            ExpiresIn=600000,
        )
        return presigned_url
    except NoCredentialsError:
        print("AWS credentials not found.")
        return None
    except Exception as e:
        print(f"Error occurred while generating presigned URL: {str(e)}")
        return None


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
                # ["--capture=sys", "-k", "test_retrieve_items", loc],
                ["--capture=sys", loc],
                plugins=[conftest, MyPlugin()],
            )

            # Restore the original stdout
            os.dup2(prev_stdout, 1)

            # Upload test output to S3 and send to Slack
            output_file.flush()
            transfer_url = generate_presigned_url(output_file.name)
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
