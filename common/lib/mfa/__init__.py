from typing import Union

from common.config import config
from common.lib.mfa.okta import okta_verify

log = config.get_logger()


async def mfa_verify(tenant: str, user: str, **kwargs) -> tuple[bool, Union[None, str]]:
    """Resolve tenant and user provider info, normalize request and pass info to provider authentication function"""

    if not config.get_tenant_specific_key(
        "temporary_elevated_access_requests.mfa.enabled", tenant, True
    ):
        log.debug({"message": "MFA disabled for tenant", "tenant": tenant})
        return True, None

    mfa_details = config.get_tenant_specific_key("secrets.mfa", tenant)
    if not mfa_details:
        raise AttributeError("MFA is not configured for this tenant")

    # TODO: Support mapping user to an MFA user if the two are not the same. e.g. noq-user vs user@noq.dev

    if mfa_details.get("provider") == "okta":
        return await okta_verify(
            tenant, user, mfa_details.get("url"), mfa_details.get("api_token"), **kwargs
        )
    else:
        raise TypeError(
            f"{mfa_details.get('provider')} if not a supported MFA provider"
        )
