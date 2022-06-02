from common.config import config

TEAR_SUPPORT_TAG = "noq-tear-supported-groups"
TEAR_USERS_TAG = "noq-tear-active-users"


def get_active_tear_users_tag(host: str) -> str:
    return config.get_host_specific_key(
        "elevated_access.active_users_tag", host, TEAR_USERS_TAG
    )


def get_tear_support_groups_tag(host: str) -> str:
    return config.get_host_specific_key(
        "elevated_access.supported_groups_tag", host, TEAR_SUPPORT_TAG
    )
