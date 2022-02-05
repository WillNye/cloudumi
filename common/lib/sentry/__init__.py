from common.exceptions.exceptions import TenantNoCentralRoleconfigured


def before_send_event(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, TenantNoCentralRoleconfigured):
            return None
    return event
