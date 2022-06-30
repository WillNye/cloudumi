from common.config import config

TEAR_SUPPORT_TAG = "noq-tear-supported-groups"
TEAR_USERS_TAG = "noq-tear-active-users"


def get_active_tear_users_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        "temporary_elevated_access_requests.active_users_tag", tenant, TEAR_USERS_TAG
    )


def get_tear_support_groups_tag(tenant: str) -> str:
    return config.get_tenant_specific_key(
        "temporary_elevated_access_requests.supported_groups_tag",
        tenant,
        TEAR_SUPPORT_TAG,
    )
