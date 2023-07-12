from datetime import datetime, timedelta
from enum import Enum

import jwt
from asyncache import cached
from cachetools import TTLCache

from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.cognito.jwt.jwt_async import decode_async
from common.lib.tenant.models import TenantDetails

log = config.get_logger(__name__)


class JwtAuthType(Enum):
    COGNITO = "cognito"


async def generate_jwt_token_from_cognito(verified_claims, tenant: str):
    return await generate_jwt_token(
        email=verified_claims["email"],
        groups=verified_claims["cognito:groups"],
        tenant=tenant,
        exp=verified_claims["exp"],
    )


async def generate_jwt_token(
    email,
    groups,
    tenant,
    roles=None,
    nbf=datetime.utcnow() - timedelta(seconds=5),
    iat=datetime.utcnow(),
    exp=None,
    eula_signed=None,
    tenant_active=None,
    mfa_setup_required=None,
    mfa_verification_required=None,
    password_reset_required=False,
    sso_user=True,
):
    tenant_details = None

    if eula_signed is None:
        tenant_details = await TenantDetails.get(tenant)
        eula_signed = bool(tenant_details.eula_info)

    if tenant_active is None:
        if not tenant_details:
            tenant_details = await TenantDetails.get(tenant)
        tenant_active = bool(tenant_details.is_active)

    groups_pending_eula = []
    roles_pending_eula = []
    if not eula_signed:
        if groups:
            groups_pending_eula = [group for group in groups]
            groups = []
        if roles:
            roles_pending_eula = [role for role in roles]
            roles = []

    if not tenant_active:
        groups = []
        roles = []

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
        "eula_signed": eula_signed,
        "tenant_active": tenant_active,
        "groups_pending_eula": groups_pending_eula,
        "additional_roles_pending_eula": roles_pending_eula,
        "mfa_setup_required": mfa_setup_required,
        "password_reset_required": password_reset_required,
        "sso_user": sso_user,
        "mfa_verification_required": mfa_verification_required,
    }

    encoded_cookie = await aio_wrapper(
        jwt.encode, session, jwt_secret, algorithm="HS256"
    )

    return encoded_cookie


@cached(cache=TTLCache(maxsize=1024, ttl=60))
async def validate_and_return_jwt_token(auth_cookie, tenant):
    jwt_secret = config.get_tenant_specific_key("secrets.jwt_secret", tenant)
    if not jwt_secret:
        raise Exception(f"jwt_secret is not defined for {tenant}")
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
            "eula_signed": decoded_jwt.get("eula_signed", False),
            "tenant_active": decoded_jwt.get("tenant_active", False),
            "groups_pending_eula": decoded_jwt.get("groups_pending_eula", []),
            "additional_roles_pending_eula": decoded_jwt.get(
                "additional_roles_pending_eula", []
            ),
            "mfa_setup_required": decoded_jwt.get("mfa_setup_required", False),
            "password_reset_required": decoded_jwt.get(
                "password_reset_required", False
            ),
            "sso_user": decoded_jwt.get("sso_user", {}),
            "mfa_verification_required": decoded_jwt.get(
                "mfa_verification_required", False
            ),
        }
    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidSignatureError,
        jwt.DecodeError,
    ):
        # Force user to reauth.
        return False


async def validate_and_authenticate_jwt_token(
    jwt_tokens: dict, tenant: str, jwt_auth_type: JwtAuthType
) -> dict:
    """Validate and authenticate a JWT token.

    Currently supports:
    - Cognito

    For instance, the Cognito JWT authenticator will validate that the claims are authentic by querying Cognito.

    :param jwt_tokens: dict. a valid JWT token set, ie: (idToken, accessToken, refreshToken) - at the very least idToken is required
    :param tenant: str. the applicable tenant
    :param jwt_auth_type: JwtAuthType. the type of JWT authenticator to use
    :return: a new JWT token to be used for the SaaS
    """
    if jwt_auth_type == JwtAuthType.COGNITO:
        region = config.get_tenant_specific_key(
            "secrets.cognito.jwt_auth.user_pool_region", tenant
        )
        userpool_id = config.get_tenant_specific_key(
            "secrets.cognito.jwt_auth.user_pool_id", tenant
        )
        app_client_id = config.get_tenant_specific_key(
            "secrets.cognito.jwt_auth.user_pool_client_id", tenant
        )

        id_token = jwt_tokens.get("idToken", {}).get("jwtToken")

        try:
            verified_claims: dict = await decode_async(
                id_token, region, userpool_id, app_client_id
            )
        except Exception as exc:
            log.exception(
                "exception", tenant=tenant, exc=exc, jwt_auth_type=jwt_auth_type.name
            )
            return {}

        return verified_claims

    return {}
