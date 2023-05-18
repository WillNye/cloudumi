import os
import tempfile
import traceback
from datetime import datetime

import boto3
from botocore.exceptions import NoCredentialsError
from tornado.web import Finish

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import TenantNoCentralRoleConfigured
from common.lib.slack import send_slack_notification_sync

log = config.get_logger()
global_slack_webhook_url = config.get("_global_.slack_webhook_url", None)

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")


def generate_presigned_url(filepath):
    filename = os.path.basename(filepath)
    temp_files_bucket = config.get("_global_.s3_buckets.temp_files")
    bucket_path = f"{timestamp}-exception"
    s3_client = boto3.client("s3")

    try:
        s3_client.upload_file(filepath, temp_files_bucket, f"{bucket_path}/{filename}")
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": temp_files_bucket, "Key": f"{bucket_path}/{filename}"},
            ExpiresIn=600000,
        )
        return presigned_url
    except NoCredentialsError:
        log.error("AWS credentials not found.")
        return None
    except Exception as e:
        log.error(f"Error occurred while generating presigned URL: {str(e)}")
        return None


def before_send_event(event, hint):
    exc_info = hint.get("exc_info", None)
    if exc_info:
        exc_type, exc_value, tb = hint["exc_info"]
        for exc in [TenantNoCentralRoleConfigured, Finish]:
            if isinstance(exc_value, exc):
                return None
        if not global_slack_webhook_url:
            return event

        formatted_traceback = "".join(traceback.format_exception(*exc_info))
        # Save the stack trace to a temporary file
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".log") as log_file:
            log_file.write(f"Traceback: {formatted_traceback}\n\n")
            log_file.write(f"Event: {json.dumps(event)}\n\n")
            log_file.write(f"Hint: {hint}\n\n")
        log_file_url = generate_presigned_url(log_file.name)
        os.remove(log_file.name)
        if log_file_url:
            message = f"An exception occurred. Log file: {log_file_url}\n\n{formatted_traceback}\n"
        else:
            message = f"An exception occurred. Failed to upload log file to S3.\n\n{formatted_traceback}"
        log_data = {}
        payload = {"text": message}
        send_slack_notification_sync(log_data, payload, global_slack_webhook_url)

    return event
