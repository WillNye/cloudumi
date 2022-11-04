import logging
import sys
import sentry_sdk
from common.config import config

log = config.get_logger()


def log_dict_func(log_level: str, account_id: str = None, role_name: str = None, tenant: str = None, exc: dict = {}, **kwargs: dict):
    if not log_level.upper() in ["debug", "info", "warning", "error", "critical", "exception"]:
        log_level = "info"
    log_data = {
        "function": f"{__name__}.{sys._getframe(1).f_code.co_name}",
        "account_id": account_id if account_id else "unknown",
        "role_name": role_name if role_name else "unknown",
        "tenant": tenant,
    }
    log_data.update(kwargs)  # Add any other log data
    if log_level.upper() in ["ERROR", "CRITICAL", "EXCEPTION"]:
        log_data["exception"] = exc
    if log_level.upper() == "EXCEPTION":
        getattr(log, getattr(logging, log_level))(log_data, exc_info=True)
    else:
        getattr(log, getattr(logging, log_level.upper()))(log_data)
    sentry_sdk.capture_exception(tags={})


def log_dict_handler(log_level: str, handler_class: object, account_id: str = None, role_name: str = None, tenant: str = None, exc: dict = {}, **kwargs: dict):
    if not log_level.upper() in ["debug", "info", "warning", "error", "critical", "exception"]:
        log_level = "info"
    log_data = {
        "function": f"{__name__}.{handler_class.__class__.__name__}.{sys._getframe().f_code.co_name}",
        "user-agent": handler_class.request.headers.get("User-Agent"),
        "request_id": handler_class.request_uuid,
        "account_id": account_id if account_id else "unknown",
        "role_name": role_name if role_name else "unknown",
        "tenant": tenant,
    }
    log_data.update(kwargs)  # Add any other log data
    if log_level.upper() in ["ERROR", "CRITICAL", "EXCEPTION"]:
        log_data["exception"] = exc
    getattr(log, getattr(logging, log_level.upper()))(log_data)
    sentry_sdk.capture_exception(tags={"user": handler_class.user})
