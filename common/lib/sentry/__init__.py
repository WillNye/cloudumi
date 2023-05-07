import os
import tempfile
import traceback

import requests
from tornado.web import Finish

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import TenantNoCentralRoleConfigured
from common.lib.slack import send_slack_notification_sync

log = config.get_logger()
global_slack_webhook_url = config.get("_global_.slack_webhook_url", None)


def upload_to_transfer_sh(file_path):
    with open(file_path, "rb") as f:
        file_name = file_path.split("/")[-1]
        response = requests.put(f"https://transfer.sh/{file_name}", files={"file": f})
        return response.text if response.status_code == 200 else None


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
        log_file_url = upload_to_transfer_sh(log_file.name)
        os.remove(log_file.name)
        if log_file_url:
            message = f"An exception occurred. Log file: {log_file_url}\n\n{formatted_traceback}\n"
        else:
            message = f"An exception occurred. Failed to upload log file to transfer.sh.\n\n{formatted_traceback}"
        log_data = {}
        payload = {"text": message}
        send_slack_notification_sync(log_data, payload, global_slack_webhook_url)

    return event
