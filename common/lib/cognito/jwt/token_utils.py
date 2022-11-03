import time
from typing import Dict, Union, Container

from jose import jwt

from common.exceptions.exceptions import CognitoJWTException
from common.lib.constants import CLIENT_ID_KEYS


async def get_unverified_headers(token: str) -> dict:
    return jwt.get_unverified_headers(token)


async def get_unverified_claims(token: str) -> dict:
    return jwt.get_unverified_claims(token)


async def check_expired(exp: int, testmode: bool = False) -> None:
    if time.time() > exp and not testmode:
        raise CognitoJWTException('Token is expired')


async def check_client_id(claims: Dict, app_client_id: Union[str, Container[str]]) -> None:
    token_use = claims['token_use']

    client_id_key: str = CLIENT_ID_KEYS.get(token_use)
    if not client_id_key:
        raise CognitoJWTException(f'Invalid token_use: {token_use}. Valid values: {list(CLIENT_ID_KEYS.keys())}')

    if isinstance(app_client_id, str):
        app_client_id = (app_client_id,)

    if claims[client_id_key] not in app_client_id:
        raise CognitoJWTException('Token was not issued for this client id audience')
