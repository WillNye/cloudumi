from datetime import datetime, timedelta

import jwt

from common.config import config
from common.lib.asyncio import aio_wrapper

log = config.get_logger()


async def generate_jwt_token(
    email,
    groups,
    tenant,
    roles=None,
    nbf=datetime.utcnow() - timedelta(seconds=5),
    iat=datetime.utcnow(),
    exp=None,
):
    if not exp:
        exp = datetime.utcnow() + timedelta(
            hours=config.get_tenant_specific_key("jwt.expiration_hours", tenant, 1)
        )
    jwt_secret = config.get_tenant_specific_key("secrets.jwt_secret", tenant)
    if not jwt_secret:
        raise Exception(f"jwt_secret is not defined for {tenant}")
    session = {
        "nbf": nbf,
        "iat": iat,
        "exp": exp,
        config.get_tenant_specific_key("jwt.attributes.email", tenant, "email"): email,
        config.get_tenant_specific_key(
            "jwt.attributes.groups", tenant, "groups"
        ): groups,
        config.get_tenant_specific_key(
            "jwt.attributes.roles", tenant, "additional_roles"
        ): roles
        or [],
        "tenant": tenant,
    }

    encoded_cookie = await aio_wrapper(
        jwt.encode, session, jwt_secret, algorithm="HS256"
    )

    return encoded_cookie


async def validate_and_return_jwt_token(auth_cookie, tenant):
    jwt_secret = config.get_tenant_specific_key("secrets.jwt_secret", tenant)
    if not jwt_secret:
        raise Exception("jwt_secret is not defined")
    try:
        decoded_jwt = jwt.decode(auth_cookie, jwt_secret, algorithms="HS256")
        email = decoded_jwt.get(
            config.get_tenant_specific_key("jwt.attributes.email", tenant, "email")
        )

        if not email:
            return False

        roles = decoded_jwt.get(
            config.get_tenant_specific_key(
                "jwt.attributes.roles", tenant, "additional_roles"
            ),
            [],
        )
        groups = decoded_jwt.get(
            config.get_tenant_specific_key("jwt.attributes.groups", tenant, "groups"),
            [],
        )
        jwt_tenant = decoded_jwt.get(
            config.get_tenant_specific_key("jwt.attributes.tenant", tenant, "tenant"),
            "",
        )
        # Security check, do not remove. tenant specified in JWT must match the tenant the user is currently connected
        # to.
        if jwt_tenant != tenant:
            return False

        exp = decoded_jwt.get("exp")

        return {
            "user": email,
            "groups": groups,
            "tenant": tenant,
            "additional_roles": roles,
            "iat": decoded_jwt.get("iat"),
            "exp": exp,
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError, jwt.DecodeError):
        # Force user to reauth.
        return False
