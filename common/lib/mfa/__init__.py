from typing import Union

from common.config import config
from common.lib.mfa.okta import okta_verify


async def mfa_verify(host: str, user: str, **kwargs) -> tuple[bool, Union[None, str]]:
    """Resolve host and user provider info, normalize request and pass info to provider authentication function"""

    mfa_details = config.get_host_specific_key("secrets.mfa", host)
    if not mfa_details:
        raise AttributeError("MFA is not configured for this tenant")

    # TODO: Support mapping user to an MFA user if the two are not the same. e.g. noq-user vs user@noq.dev

    if mfa_details.get("provider") == "okta":
        return await okta_verify(
            host, user, mfa_details.get("url"), mfa_details.get("api_token"), **kwargs
        )
    else:
        raise TypeError(
            f"{mfa_details.get('provider')} if not a supported MFA provider"
        )
