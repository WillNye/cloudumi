from typing import Dict

CLIENT_ID_KEYS: Dict[str, str] = {"access": "client_id", "id": "aud"}
PUBLIC_KEYS_URL_TEMPLATE = (
    "https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json"
)
