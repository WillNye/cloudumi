from common.exceptions.exceptions import TenantNoCentralRoleConfigured


def before_send_event(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, TenantNoCentralRoleConfigured):
            return None
    return event
