from typing import Dict

CLIENT_ID_KEYS: Dict[str, str] = {"access": "client_id", "id": "aud"}
# TODO (mdaue), we should be getting this from the oidc endpoint, and it must definitely
# not be declared a constant because Amazon can change it at any time. See `populate_oidc_config()`
# Example: https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EQ5XHIluC/.well-known/openid-configuration
# And we can't assume we will be using Cognito only for SSO, this must be generic.
PUBLIC_KEYS_URL_TEMPLATE = (
    "https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json"
)
