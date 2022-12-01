from tornado.web import Finish

from common.exceptions.exceptions import TenantNoCentralRoleConfigured


def before_send_event(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        for exc in [TenantNoCentralRoleConfigured, Finish]:
            if isinstance(exc_value, exc):
                return None
    return event
