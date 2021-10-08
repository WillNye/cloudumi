from datetime import datetime, timedelta

import jwt
from asgiref.sync import sync_to_async

from cloudumi_common.config import config

log = config.get_logger()


async def generate_jwt_token(
    email,
    groups,
    host,
    nbf=datetime.utcnow() - timedelta(seconds=5),
    iat=datetime.utcnow(),
    exp=None,
):
    if not exp:
        exp = datetime.utcnow() + timedelta(
            hours=config.get_host_specific_key(
                f"site_configs.{host}.jwt.expiration_hours", host, 1
            )
        )
    jwt_secret = config.get_host_specific_key(f"site_configs.{host}.jwt_secret", host)
    if not jwt_secret:
        raise Exception("jwt_secret is not defined")
    session = {
        "nbf": nbf,
        "iat": iat,
        "exp": exp,
        config.get_host_specific_key(
            f"site_configs.{host}.jwt.attributes.email", host, "email"
        ): email,
        config.get_host_specific_key(
            f"site_configs.{host}.jwt.attributes.groups", host, "groups"
        ): groups,
        "host": host,
    }

    encoded_cookie = await sync_to_async(jwt.encode)(
        session, jwt_secret, algorithm="HS256"
    )

    return encoded_cookie


async def validate_and_return_jwt_token(auth_cookie, host):
    jwt_secret = config.get_host_specific_key(f"site_configs.{host}.jwt_secret", host)
    if not jwt_secret:
        raise Exception("jwt_secret is not defined")
    try:
        decoded_jwt = jwt.decode(auth_cookie, jwt_secret, algorithms="HS256")
        email = decoded_jwt.get(
            config.get_host_specific_key(
                f"site_configs.{host}.jwt.attributes.email", host, "email"
            )
        )

        if not email:
            return False

        groups = decoded_jwt.get(
            config.get_host_specific_key(
                f"site_configs.{host}.jwt.attributes.groups", host, "groups"
            ),
            [],
        )
        jwt_host = decoded_jwt.get(
            config.get_host_specific_key(
                f"site_configs.{host}.jwt.attributes.host", host, "host"
            ),
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
            "iat": decoded_jwt.get("iat"),
            "exp": exp,
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError, jwt.DecodeError):
        # Force user to reauth.
        return False
