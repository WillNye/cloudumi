import base64
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Union

import jsonschema
import jwt
from cryptography.hazmat.backends.openssl.rsa import _RSAPublicKey

import common.lib.noq_json as json
from common.aws.utils import ResourceAccountCache
from common.config import config
from common.config.models import ModelAdapter
from common.config.tenant_config import TenantConfig
from common.lib.crypto import CryptoSign
from common.lib.generic import is_in_group
from common.lib.plugins import get_plugin_by_name
from common.models import ExtendedRequestModel, SpokeAccount

log = config.get_logger(__name__)


class AuthenticatedResponse:
    def __init__(self, **kwargs):
        self.authenticated: bool = kwargs.get("authenticated", False)
        self.redirect: str = kwargs.get("redirect", "")

    def get(self, query):
        return self.__dict__.get(query)

    def to_json(self):
        if isinstance(self.value, list):
            self.value = ",".join(self.value)
        d = {
            "name": self.name,
            "attributeType": self.type,
            "attributeValue": self.value,
            "sensitive": self.sensitive,
            "immutable": self.immutable,
        }
        return json.dumps(d)


async def generate_auth_token(
    user, ip, challenge_uuid, request_object, expiration=None
):
    tenant = request_object.get_tenant_name()
    stats = get_plugin_by_name(
        config.get("_global_.plugins.metrics", "cmsaas_metrics")
    )()
    stats.count("generate_auth_token")
    if not expiration:
        expiration = config.get_tenant_specific_key(
            "challenge.token_expiration", tenant, 3600
        )
    log_data = {
        "user": user,
        "ip": ip,
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Generating token for user",
        "challenge_uuid": challenge_uuid,
        "tenant": tenant,
    }
    log.debug(log_data)
    current_time = int(time.time())
    valid_before = current_time + expiration
    valid_after = current_time

    auth_token = {
        "user": user,
        "ip": ip,
        "challenge_uuid": challenge_uuid,
        "valid_before": valid_before,
        "valid_after": valid_after,
        "tenant": tenant,
    }

    to_sign = (
        "{{'user': '{0}', 'ip': '{1}', 'challenge_uuid'': '{2}', "
        "'valid_before'': '{3}', 'valid_after'': '{4}', 'tenant'': '{5}'}}"
    ).format(user, ip, challenge_uuid, valid_before, valid_after, tenant)
    crypto = CryptoSign(tenant)
    sig = crypto.sign(to_sign)

    auth_token["sig"] = sig
    return base64.b64encode(json.dumps(auth_token).encode())


async def validate_auth_token(user, ip, token, request_object):
    tenant = request_object.get_tenant_name()
    stats = get_plugin_by_name(
        config.get("_global_.plugins.metrics", "cmsaas_metrics")
    )()
    stats.count("validate_auth_token")
    log_data = {
        "user": user,
        "ip": ip,
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Validating token for user",
        "tenant": tenant,
    }
    log.debug(log_data)
    if not token:
        stats.count("validate_auth_token.no_token")
        msg = f"No token passed. User: {user}. IP: {ip}."
        log.error(msg, exc_info=True)
        raise Exception(msg)
    decoded_token = base64.b64decode(token)
    auth_token = json.loads(decoded_token)
    current_time = int(time.time())

    if auth_token.get("user") != user:
        stats.count("validate_auth_token.user_mismatch")
        msg = f"Auth token has a different user: {auth_token.get('user')}. User passed to function: {user}"
        log.error(msg, exc_info=True)
        raise Exception(msg)

    if auth_token.get("ip") != ip:
        stats.count("validate_auth_token.ip_mismatch")
        msg = f"Auth token has a different IP: {auth_token.get('ip')}. IP passed to function: {ip}"
        log.error(msg, exc_info=True)
        raise Exception(msg)

    if (
        auth_token.get("valid_before") < current_time
        or auth_token.get("valid_after") > current_time
    ):
        stats.count("validate_auth_token.expiration_error")
        msg = (
            f"Auth token has expired. valid_before: {auth_token.get('valid_before')}. "
            f"valid_after: {auth_token.get('valid_after')}. Current_time: {current_time}"
        )
        log.error(msg, exc_info=True)
        raise Exception(msg)

    if auth_token.get("tenant") != tenant:
        stats.count("validate_auth_token.invalid_tenant")
        msg = f"Auth token has a different tenant: {auth_token.get('tenant')}. tenant passed to function: {tenant}"
        log.error(msg, exc_info=True)
        raise Exception(msg)

    to_verify = (
        "{{'user': '{0}', 'ip': '{1}', 'challenge_uuid'': '{2}', "
        "'valid_before'': '{3}', 'valid_after'': '{4}', 'tenant'': '{5}'}}"
    ).format(
        auth_token.get("user"),
        auth_token.get("ip"),
        auth_token.get("challenge_uuid"),
        auth_token.get("valid_before"),
        auth_token.get("valid_after"),
        auth_token.get("tenant"),
    )
    crypto = CryptoSign(tenant)
    token_details = {
        "valid": crypto.verify(to_verify, auth_token.get("sig")),
        "user": auth_token.get("user"),
    }

    return token_details


def is_tenant_admin(user: str, user_groups: List[str], tenant: str):
    tenant_config = TenantConfig.get_instance(tenant)
    for application_admin in tenant_config.application_admins:
        if user == application_admin or application_admin in user_groups:
            return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_admin", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_admin", tenant, []
            ),
        ],
    ):
        return True
    return False


async def get_accounts_user_can_view_resources_for(user, groups, tenant) -> set[str]:
    spoke_roles = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).list
    allowed = set()
    for spoke_role in spoke_roles:
        if is_tenant_admin(user, groups, tenant):
            allowed.add(spoke_role.get("account_id"))
            continue
        if not spoke_role.get("restrict_viewers_of_account_resources"):
            allowed.add(spoke_role.get("account_id"))
            continue
        if user in spoke_role.get("viewers", []) or user in spoke_role.get(
            "owners", []
        ):
            allowed.add(spoke_role.get("account_id"))
            continue
        for group in groups:
            if group in spoke_role.get("viewers", []) or group in spoke_role.get(
                "owners", []
            ):
                allowed.add(spoke_role.get("account_id"))
                break
    return allowed


async def get_accounts_user_can_edit_resources_for(user, groups, tenant) -> set[str]:
    spoke_roles = ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).list
    allowed_accounts = set()
    for spoke_role in spoke_roles:
        if not spoke_role.get("delegate_admin_to_owner"):
            continue
        if user in spoke_role.get("owners", []):
            allowed_accounts.add(spoke_role.get("account_id"))
            continue
        for group in groups:
            if group in spoke_role.get("owners", []):
                allowed_accounts.add(spoke_role.get("account_id"))
                break
    return allowed_accounts


async def user_can_edit_resources(user, groups, tenant, account_ids) -> bool:
    can_edit_resource = False
    if is_tenant_admin(user, groups, tenant):
        return True

    if len(account_ids) == 0:
        return can_edit_resource

    allowed_accounts = await get_accounts_user_can_edit_resources_for(
        user, groups, tenant
    )
    for account_id in account_ids:
        if account_id in allowed_accounts:
            can_edit_resource = True
        else:
            can_edit_resource = False
            break

    return can_edit_resource


def can_admin_identity(user: str, user_groups: List[str], tenant: str):
    if is_tenant_admin(user, user_groups, tenant):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_admin_identity", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_admin_identity",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def can_create_roles(user: str, user_groups: List[str], tenant: str) -> bool:
    if is_tenant_admin(user, user_groups, tenant):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_create_roles", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_create_roles", tenant, []
            ),
        ],
    ):
        return True
    return False


async def get_extended_request_account_ids(
    extended_request: ExtendedRequestModel, tenant: str
) -> set[str]:
    accounts = set()

    if account_id := extended_request.principal.account_id:
        return {account_id}

    for change in extended_request.changes.changes:
        arn = change.principal.principal_arn
        if change.change_type in [
            "resource_policy",
            "sts_resource_policy",
        ]:
            arn = change.arn
        accounts.add(await ResourceAccountCache.get(tenant, arn))
    return accounts


async def get_extended_request_allowed_approvers(
    extended_request: ExtendedRequestModel, tenant: str
):
    allowed_admins = set()
    for change in extended_request.changes.changes:
        arn = change.principal.principal_arn
        if change.change_type in [
            "resource_policy",
            "sts_resource_policy",
        ]:
            arn = change.arn

        account_id = change.principal.account_id or (
            await ResourceAccountCache.get(tenant, arn)
        )
        admins = await get_account_delegated_admins(account_id, tenant)
        allowed_admins.update(admins)
    return list(allowed_admins)


async def get_account_delegated_admins(account_id, tenant):
    tenant_config = TenantConfig.get_instance(tenant)
    spoke_role_adapter = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
    )
    allowed_admins = set()

    try:
        spoke_role = spoke_role_adapter.first
        if spoke_role.delegate_admin_to_owner:
            allowed_admins.update(spoke_role.owners)
    except ValueError:
        # Spoke account not available
        pass

    allowed_admins.update(tenant_config.application_admins)

    admin_groups = [
        *config.get_tenant_specific_key("groups.can_admin_policies", tenant, []),
        *config.get_tenant_specific_key(
            "dynamic_config.groups.can_admin_policies",
            tenant,
            [],
        ),
    ]
    allowed_admins.update(admin_groups)

    return list(allowed_admins)


async def populate_approve_reject_policy(
    extended_request: ExtendedRequestModel, groups, tenant, user: str
) -> dict[str, Any]:
    request_config = {}

    for change in extended_request.changes.changes:
        account_id = extended_request.principal.account_id

        if not account_id:
            arn = change.principal.principal_arn
            if change.change_type in [
                "resource_policy",
                "sts_resource_policy",
            ]:
                arn = change.arn
            account_id = await ResourceAccountCache.get(tenant, arn)

        is_owner = await can_admin_policies(user, groups, tenant, [account_id])
        allowed_admins = await get_account_delegated_admins(account_id, tenant)
        request_config[change.id] = {
            "can_approve_policy": False if not is_owner else True,
            "allowed_admins": allowed_admins,
        }
    return request_config


async def can_admin_policies(
    user: str, user_groups: List[str], tenant: str, account_ids: set[str] = None
) -> bool:
    if not account_ids:
        account_ids = set()
    if await user_can_edit_resources(user, user_groups, tenant, account_ids):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_admin_policies", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_admin_policies",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def can_delete_iam_principals_app(app_name, tenant):
    if app_name in [
        *config.get_tenant_specific_key("groups.can_delete_roles_apps", tenant, []),
        *config.get_tenant_specific_key(
            "dynamic_config.groups.can_delete_roles_apps", tenant, []
        ),
    ]:
        return True
    return False


def can_delete_iam_principals(
    user: str,
    user_groups: List[str],
    tenant: str,
) -> bool:
    if is_tenant_admin(user, user_groups, tenant):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            # TODO: Officially deprecate groups.can_delete_roles config key
            *config.get_tenant_specific_key("groups.can_delete_roles", tenant, []),
            # TODO: Officially deprecate dynamic_config.groups.can_delete_roles config key
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_delete_roles", tenant, []
            ),
            *config.get_tenant_specific_key(
                "groups.can_delete_iam_principals", tenant, []
            ),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_delete_iam_principals",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def can_edit_dynamic_config(user: str, user_groups: List[str], tenant: str) -> bool:
    if is_tenant_admin(user, user_groups, tenant):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_edit_config", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_edit_config", tenant, []
            ),
        ],
    ):
        return True
    return False


def can_edit_attributes(
    user: str,
    user_groups: List[str],
    group_info: Optional[Any],
    tenant: str,
) -> bool:
    if is_tenant_admin(user, user_groups, tenant):
        return True

    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_admin_restricted", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_admin_restricted",
                tenant,
                [],
            ),
        ],
    ):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_edit_attributes", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_edit_attributes",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def can_modify_members(
    tenant: str, user: str, user_groups: List[str], group_info: Optional[Any]
) -> bool:
    # No users can modify members on restricted groups
    if group_info and group_info.restricted:
        return False

    if is_tenant_admin(user, user_groups, tenant):
        return True

    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_admin_restricted", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_admin_restricted",
                tenant,
                [],
            ),
        ],
    ):
        return True

    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key("groups.can_modify_members", tenant, []),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_modify_members",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def can_edit_sensitive_attributes(
    user: str, user_groups: List[str], group_info: Optional[Any], tenant: str
) -> bool:
    if is_tenant_admin(user, user_groups, tenant):
        return True
    if is_in_group(
        user,
        user_groups,
        [
            *config.get_tenant_specific_key(
                "groups.can_edit_sensitive_attributes", tenant, []
            ),
            *config.get_tenant_specific_key(
                "dynamic_config.groups.can_edit_sensitive_attributes",
                tenant,
                [],
            ),
        ],
    ):
        return True
    return False


def is_sensitive_attr(attribute, tenant):
    for attr in [
        *config.get_tenant_specific_key("groups.attributes.boolean", tenant, []),
        *config.get_tenant_specific_key(
            "dynamic_config.groups.attributes.boolean", tenant, []
        ),
    ]:
        if attr.get("name") == attribute:
            return attr.get("sensitive", False)

    for attr in [
        *config.get_tenant_specific_key("groups.attributes.list", tenant, []),
        *config.get_tenant_specific_key(
            "dynamic_config.groups.attributes.list", tenant, []
        ),
    ]:
        if attr.get("name") == attribute:
            return attr.get("sensitive", False)
    return False


class Error(Exception):
    """Base class for exceptions in this module."""


class AuthenticationError(Error):
    """Exception raised for AuthN errors."""

    def __init__(self, message):
        self.message = message


def mk_jwt_validator(
    verification_str: _RSAPublicKey,
    header_cfg: Dict[str, Dict[str, List[str]]],
    payload_cfg: Dict[str, Dict[str, List[str]]],
) -> Callable:
    def validate_jwt(jwt_str):
        try:
            tkn = jwt.decode(
                jwt_str, verification_str, algorithms=header_cfg["alg"]["enum"]
            )
        except jwt.InvalidSignatureError:
            raise AuthenticationError("Invalid Token Signature")
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token Expired")
        except jwt.InvalidAudienceError:
            raise AuthenticationError("Invalid Token Audience")
        except jwt.DecodeError:
            raise AuthenticationError("Invalid Token")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Malformed Token")

        try:
            jsonschema.validate(tkn, payload_cfg)
        except jsonschema.ValidationError as e:
            raise AuthenticationError(e.message)
        return tkn

    return validate_jwt


class UnsupportedKeyTypeError(Error):
    """Exception raised unsupported JWK Errors."""

    def __init__(self, message):
        self.message = message


def mk_jwks_validator(
    jwk_set: List[Dict[str, Union[str, List[str]]]],
    header_cfg: Dict[str, Dict[str, List[str]]],
    payload_cfg: Dict[str, Dict[str, List[str]]],
) -> Callable:
    keys = []
    for j in jwk_set:
        if j["kty"] == "RSA":
            j_str = json.dumps(j)
            keys.append(jwt.algorithms.RSAAlgorithm.from_jwk(j_str))
        else:
            raise UnsupportedKeyTypeError("Unsupported Key Type: %s" % j["kty"])

    validators = [mk_jwt_validator(k, header_cfg, payload_cfg) for k in keys]

    def validate_jwt(jwt_str):
        result = None
        for v in validators:
            try:
                result = v(jwt_str)
            except AuthenticationError as e:
                result = e
            else:
                break
        if isinstance(result, Exception):
            raise result
        return result

    return validate_jwt
