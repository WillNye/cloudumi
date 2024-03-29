from typing import Container, Dict, List, Optional, Union

import aiohttp
from async_lru import alru_cache
from jose import jwk
from jose.utils import base64url_decode

from common.config import config
from common.exceptions.exceptions import CognitoJWTException
from common.lib.cognito.jwt.token_utils import (
    check_client_id,
    check_expired,
    get_unverified_claims,
    get_unverified_headers,
)
from common.lib.constants import PUBLIC_KEYS_URL_TEMPLATE


@alru_cache(maxsize=1)
async def get_keys_async(keys_url: str) -> List[dict]:
    response = {}
    if keys_url.startswith("https"):  # Enforce https
        async with aiohttp.ClientSession() as session:
            async with session.get(keys_url) as resp:
                response = await resp.json()
    return response.get("keys")


async def get_public_key_async(token: str, region: str, userpool_id: str):
    keys_url: str = config.get(
        "_global_.auth.cognito_jwks_path",
        PUBLIC_KEYS_URL_TEMPLATE.format(region, userpool_id),
    )
    keys: list = await get_keys_async(keys_url)
    headers = get_unverified_headers(token)
    kid = headers["kid"]

    key = list(filter(lambda k: k["kid"] == kid, keys))
    if not key or key == "" or key == 0:
        raise CognitoJWTException("Public key not found in jwks.json")
    else:
        key = key[0]

    return jwk.construct(key)


async def decode_async(
    token: str,
    region: str,
    userpool_id: str,
    app_client_id: Optional[Union[str, Container[str]]] = None,
) -> Dict:
    message, encoded_signature = str(token).rsplit(".", 1)

    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

    public_key = await get_public_key_async(token, region, userpool_id)

    if not public_key.verify(message.encode("utf-8"), decoded_signature):
        raise CognitoJWTException("Signature verification failed")

    claims = await get_unverified_claims(token)
    await check_expired(claims["exp"])

    if app_client_id:
        await check_client_id(claims, app_client_id)

    return claims
