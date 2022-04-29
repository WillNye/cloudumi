from datetime import datetime, timedelta

import jwt

from common.config import config
from common.lib.asyncio import aio_wrapper

log = config.get_logger()


async def generate_jwt_token(
    email,
    groups,
    host,
    roles=None,
    nbf=datetime.utcnow() - timedelta(seconds=5),
    iat=datetime.utcnow(),
    exp=None,
):
    if not exp:
        exp = datetime.utcnow() + timedelta(
            hours=config.get_host_specific_key("jwt.expiration_hours", host, 1)
        )
    jwt_secret = config.get_host_specific_key("secrets.jwt_secret", host)
    if not jwt_secret:
        raise Exception(f"jwt_secret is not defined for {host}")
    session = {
        "nbf": nbf,
        "iat": iat,
        "exp": exp,
        config.get_host_specific_key("jwt.attributes.email", host, "email"): email,
        config.get_host_specific_key("jwt.attributes.groups", host, "groups"): groups,
        config.get_host_specific_key(
            "jwt.attributes.roles", host, "additional_roles"
        ): roles
        or [],
        "host": host,
    }

    encoded_cookie = await aio_wrapper(
        jwt.encode, session, jwt_secret, algorithm="HS256"
    )

    return encoded_cookie


async def validate_and_return_jwt_token(auth_cookie, host):
    jwt_secret = config.get_host_specific_key("secrets.jwt_secret", host)
    if not jwt_secret:
        raise Exception("jwt_secret is not defined")
    try:
        decoded_jwt = jwt.decode(auth_cookie, jwt_secret, algorithms="HS256")
        email = decoded_jwt.get(
            config.get_host_specific_key("jwt.attributes.email", host, "email")
        )

        if not email:
            return False

        roles = decoded_jwt.get(
            config.get_host_specific_key("jwt.attributes.roles", host, "roles"),
            [],
        )
        groups = decoded_jwt.get(
            config.get_host_specific_key("jwt.attributes.groups", host, "groups"),
            [],
        )
        jwt_host = decoded_jwt.get(
            config.get_host_specific_key("jwt.attributes.host", host, "host"),
            "",
        )
        # Security check, do not remove. Host specified in JWT must match the host the user is currently connected
        # to.
        if jwt_host != host:
            return False

        exp = decoded_jwt.get("exp")

        return {
            "user": email,
            "groups": groups,
            "host": host,
            "additional_roles": roles,
            "iat": decoded_jwt.get("iat"),
            "exp": exp,
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError, jwt.DecodeError):
        # Force user to reauth.
        return False
