import asyncio
import base64
import operator
import re
import sys
from datetime import datetime, timedelta
from functools import reduce
from typing import Any

import jwt
import pytz
import sentry_sdk
import tornado.httpclient
from furl import furl
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from jwt.exceptions import DecodeError
from tornado import httputil

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import MissingConfigurationValue, UnableToAuthenticate
from common.lib.auth.user_management import maybe_create_users_groups_in_database
from common.lib.cognito.identity import CognitoUserClient
from common.lib.generic import should_force_redirect
from common.lib.jwt import generate_jwt_token

log = config.get_logger()


async def populate_oidc_config(tenant):
    http_client = tornado.httpclient.AsyncHTTPClient()
    metadata_url = config.get_tenant_specific_key(
        "get_user_by_oidc_settings.metadata_url", tenant
    )

    if metadata_url:
        res = await http_client.fetch(
            metadata_url,
            method="GET",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        oidc_config = json.loads(res.body)
    else:
        authorization_endpoint = config.get_tenant_specific_key(
            "get_user_by_oidc_settings.authorization_endpoint",
            tenant,
        )
        token_endpoint = config.get_tenant_specific_key(
            "get_user_by_oidc_settings.token_endpoint", tenant
        )
        jwks_uri = config.get_tenant_specific_key(
            "get_user_by_oidc_settings.jwks_uri", tenant
        )
        if not (authorization_endpoint or token_endpoint or jwks_uri):
            raise MissingConfigurationValue("Missing OIDC Configuration.")
        oidc_config = {
            "authorization_endpoint": authorization_endpoint,
            "token_endpoint": token_endpoint,
            "jwks_uri": jwks_uri,
        }
    client_id = config.get_tenant_specific_key("secrets.auth.oidc.client_id", tenant)
    client_secret = config.get_tenant_specific_key(
        "secrets.auth.oidc.client_secret", tenant
    )
    if not client_id:
        raise MissingConfigurationValue("Missing OIDC ID")
    oidc_config["client_id"] = client_id
    oidc_config["client_secret"] = client_secret
    oidc_config["jwt_keys"] = {}
    jwks_uris = [oidc_config["jwks_uri"]]
    jwks_uris.extend(
        config.get_tenant_specific_key(
            "get_user_by_oidc_settings.extra_jwks_uri", tenant, []
        )
    )
    for jwks_uri in jwks_uris:
        # Fetch jwks_uri for jwt validation
        res = await http_client.fetch(
            jwks_uri,
            method="GET",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        jwks_data = json.loads(res.body)
        for k in jwks_data["keys"]:
            key_type = k["kty"]
            key_id = k["kid"]
            if key_type == "RSA":
                oidc_config["jwt_keys"][key_id] = RSAAlgorithm.from_jwk(json.dumps(k))
            elif key_type == "EC":
                oidc_config["jwt_keys"][key_id] = ECAlgorithm.from_jwk(json.dumps(k))
            else:
                raise MissingConfigurationValue(
                    f"OIDC/OAuth2 key type not recognized. Detected key type: {key_type}."
                )
    return oidc_config


async def get_roles_from_token(tenant, token: dict[str, Any]) -> set:
    roles = set()
    custom_role_attributes = config.get_tenant_specific_key(
        "get_user_by_oidc_settings.custom_role_attributes", tenant, []
    )
    for role_attribute in custom_role_attributes:
        attribute_name = role_attribute["name"]
        delimiter = role_attribute.get("delimiter", ",")
        regex = role_attribute.get("regex", "(.*)")
        role_match = role_attribute.get("role_match", "\\1")

        if not token.get(attribute_name):
            continue
        raw_role_values = token[role_attribute["name"]].split(delimiter)
        regexp = re.compile(regex, re.IGNORECASE)

        for role_val in raw_role_values:
            roles.add(re.sub(regexp, role_match, role_val))
    return roles


async def authenticate_user_by_oidc(request, return_200=False, force_redirect=None):
    jwt_tokens = {}
    try:
        request_body: dict = json.loads(request.request.body)
        if request_body.get("idToken").get("jwtToken", {}):
            jwt_tokens = request_body
    except Exception:
        pass
    id_token = jwt_tokens.get("idToken", {}).get("jwtToken", None)
    access_token = jwt_tokens.get("accessToken", {}).get("jwtToken", None)
    full_host = request.request.headers.get("X-Forwarded-Host")
    http_client = tornado.httpclient.AsyncHTTPClient()
    if not full_host:
        full_host = request.get_tenant()
    tenant = request.get_tenant_name()

    cognito_enabled = False
    if (
        config.get_tenant_specific_key(
            "get_user_by_oidc_settings.jwt_groups_key", tenant
        )
        == "cognito:groups"
    ):
        cognito_enabled = True
    groups = []
    decoded_access_token = {}
    oidc_config = await populate_oidc_config(tenant)
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    code = request.get_argument("code", None)
    protocol = request.request.protocol
    if "https://" in config.get_tenant_specific_key(
        "url", tenant
    ) or "https://" in request.request.headers.get("Referer", ""):
        # If we're behind a load balancer that terminates tls for us, request.request.protocol will be "http://" and our
        # oidc redirect will be invalid
        protocol = "https"
    if force_redirect is None:
        force_redirect = await should_force_redirect(request.request)

    # The endpoint where we want our OIDC provider to redirect us back to perform auth
    oidc_redirect_uri = f"{protocol}://{full_host}/auth"

    # The endpoint where the user wants to be sent after authentication. This will be stored in the state
    after_redirect_uri = request.request.arguments.get("redirect_url", [""])[0]
    if not after_redirect_uri:
        after_redirect_uri = request.request.arguments.get("state", [""])[0]
    if after_redirect_uri and isinstance(after_redirect_uri, bytes):
        after_redirect_uri = after_redirect_uri.decode("utf-8")
    if not after_redirect_uri and force_redirect:
        # If we're forcing a redirect, we need to redirect to the same page.
        after_redirect_uri = request.request.uri
    if not after_redirect_uri:
        after_redirect_uri = config.get_tenant_specific_key(
            "url", tenant, f"{protocol}://{full_host}/"
        )

    if not code and not id_token:
        parsed_after_redirect_uri = furl(after_redirect_uri)
        code = parsed_after_redirect_uri.args.get("code")
        if code:
            del parsed_after_redirect_uri.args["code"]
        after_redirect_uri = parsed_after_redirect_uri.url

    if not code and not id_token:
        args = {"response_type": "code"}
        client_scope = config.get_tenant_specific_key(
            "get_user_by_oidc_settings.client_scopes", tenant
        )
        if (
            config.get_tenant_specific_key(
                "get_user_by_oidc_settings.include_admin_scope", tenant, True
            )
            and "aws.cognito.signin.user.admin" not in client_scope
        ):
            client_scope.append("aws.cognito.signin.user.admin")
        if request.request.uri is not None:
            args["redirect_uri"] = oidc_redirect_uri
        args["client_id"] = oidc_config["client_id"]
        if client_scope:
            args["scope"] = " ".join(client_scope)

        args["state"] = after_redirect_uri

        if force_redirect:
            request.redirect(
                httputil.url_concat(oidc_config["authorization_endpoint"], args)
            )
        else:
            if not return_200:
                # GraphQL (New UI) will not work if we return 403
                request.set_status(403)
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": httputil.url_concat(
                        oidc_config["authorization_endpoint"], args
                    ),
                    "reason": "unauthenticated",
                    "message": "User is not authenticated. Redirect to authenticate",
                }
            )
        raise tornado.web.Finish()
    if not id_token or not access_token:
        try:
            client_id = oidc_config["client_id"]
            # exchange the authorization code with the access token
            grant_type = config.get_tenant_specific_key(
                "get_user_by_oidc_settings.grant_type",
                tenant,
                "authorization_code",
            )
            authorization_header = f"{client_id}:{oidc_config['client_secret']}"
            authorization_header_encoded = base64.b64encode(
                authorization_header.encode("UTF-8")
            ).decode("UTF-8")
            url = f"{oidc_config['token_endpoint']}"
            client_scope = config.get_tenant_specific_key(
                "get_user_by_oidc_settings.client_scopes", tenant
            )
            if (
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.include_admin_scope", tenant, True
                )
                and "aws.cognito.signin.user.admin" not in client_scope
            ):
                client_scope.append("aws.cognito.signin.user.admin")
            if client_scope:
                client_scope = " ".join(client_scope)
            try:
                client_secret = oidc_config.get("client_secret")
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                }
                if client_secret:
                    # If authorization header is included in a token exchange request
                    # for a client without a client_secret, Cognito will return an
                    # ambiguous error.
                    headers["Authorization"] = "Basic %s" % authorization_header_encoded
                body = f"grant_type={grant_type}&code={code}&redirect_uri={oidc_redirect_uri}&scope={client_scope}"
                if cognito_enabled:
                    body += f"&client_id={client_id}"
                token_exchange_response = await http_client.fetch(
                    url,
                    method="POST",
                    headers=headers,
                    body=f"grant_type={grant_type}&code={code}&redirect_uri={oidc_redirect_uri}&scope={client_scope}",
                )
            except tornado.httpclient.HTTPError:
                raise

            token_exchange_response_body_dict = json.loads(token_exchange_response.body)
            id_token = token_exchange_response_body_dict.get(
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.id_token_response_key",
                    tenant,
                    "id_token",
                )
            )
            access_token = token_exchange_response_body_dict.get(
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.access_token_response_key",
                    tenant,
                    "access_token",
                )
            )
        except Exception as e:
            log_data["error"] = e
            log.error(log_data, exc_info=True)
            return
    try:
        header = jwt.get_unverified_header(id_token)
        key_id = header["kid"]
        algorithm = header["alg"]
        if algorithm == "none" or not algorithm:
            raise UnableToAuthenticate(
                "ID Token header does not specify a signing algorithm."
            )
        pub_key = oidc_config["jwt_keys"][key_id]
        # This will raises errors if the audience isn't right or if the token is expired or has other errors.
        decoded_id_token = jwt.decode(
            id_token,
            pub_key,
            audience=oidc_config["client_id"],
            algorithms=algorithm,
        )

        email = decoded_id_token.get(
            config.get_tenant_specific_key(
                "get_user_by_oidc_settings.jwt_email_key",
                tenant,
                "email",
            )
        )
        mfa_setup_required = None
        if cognito_enabled and not decoded_id_token.get("identities"):
            user_client = CognitoUserClient.tenant_client(tenant)
            mfa_configured = user_client.user_mfa_enabled(email)
            if not mfa_configured and config.get_tenant_specific_key(
                "get_user_by_oidc_settings.enable_mfa", tenant, True
            ):
                # If MFA isn't enabled for the user, begin the setup process
                mfa_setup_required = await user_client.get_mfa_secret(
                    email, access_token=access_token, tenant=tenant
                )
                after_redirect_uri = f"{protocol}://{full_host}/mfa"

        # For google auth, the access_token does not contain JWT-parsable claims.
        if config.get_tenant_specific_key(
            "get_user_by_oidc_settings.get_groups_from_access_token",
            tenant,
            True,
        ):
            try:
                header = jwt.get_unverified_header(access_token)
                key_id = header["kid"]
                algorithm = header["alg"]
                if algorithm == "none" or not algorithm:
                    raise UnableToAuthenticate(
                        "Access Token header does not specify a signing algorithm."
                    )
                pub_key = oidc_config["jwt_keys"][key_id]
                # This will raises errors if the audience isn't right or if the token is expired or has other
                # errors.
                decoded_access_token = jwt.decode(
                    access_token,
                    pub_key,
                    audience=config.get_tenant_specific_key(
                        "get_user_by_oidc_settings.access_token_audience",
                        tenant,
                    ),
                    algorithms=algorithm,
                )
            except (DecodeError, KeyError) as e:
                # This exception occurs when the access token is opaque or otherwise not JWT-parsable.
                # It is expected with some IdPs.
                log.debug(
                    {
                        **log_data,
                        "message": (
                            "Unable to derive user's groups from access_token. Attempting to get groups through "
                            "userinfo endpoint. "
                        ),
                        "error": e,
                        "user": email,
                    }
                )
                log.debug(log_data, exc_info=True)
                groups = []

        email = email or decoded_id_token.get(
            config.get_tenant_specific_key(
                "get_user_by_oidc_settings.jwt_email_key",
                tenant,
                "email",
            )
        )

        if not email:
            raise UnableToAuthenticate("Unable to determine user from ID Token")

        role_allowance_sets = await asyncio.gather(
            get_roles_from_token(tenant, decoded_id_token),
            get_roles_from_token(tenant, decoded_access_token),
        )
        role_allowances = reduce(operator.or_, role_allowance_sets)
        groups = (
            groups
            or decoded_access_token.get(
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.jwt_groups_key",
                    tenant,
                    "groups",
                ),
            )
            or decoded_id_token.get(
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.jwt_groups_key",
                    tenant,
                    "groups",
                ),
                [],
            )
        )

        # Groups from the token are not always in the correct format. For JumpCloud,
        # The format is a string that looks like valid JSON, but isn't. Example:
        # '[Cool%2C+and+Stuff%7C%7C%7C%7E%21%40%24%40%23%24%25%24%40%25%26%24%25%26*%5E%29%28%26*_%2B_, group_with_underscores, All Users, Engineering Group, Other group with a sane name]'
        if (
            groups
            and isinstance(groups, str)
            and groups.startswith("[")
            and groups.endswith("]")
        ):
            try:
                groups = json.loads(groups)
            except json.JSONDecodeError:
                try:
                    groups = groups[1:-1].split(", ")
                except Exception as e:
                    log.debug(
                        {
                            **log_data,
                            "message": ("Unable to parse user's groups from id token"),
                            "error": e,
                            "user": email,
                            "groups": groups,
                        }
                    )
                    sentry_sdk.capture_exception()
        if (
            not groups
            and oidc_config.get("userinfo_endpoint")
            and config.get_tenant_specific_key(
                "get_user_by_oidc_settings.get_groups_from_userinfo_endpoint",
                tenant,
                True,
            )
        ):
            user_info = await http_client.fetch(
                oidc_config["userinfo_endpoint"],
                method="GET",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": "Bearer %s" % access_token,
                    "Accept": "application/json",
                },
            )
            groups = json.loads(user_info.body).get(
                config.get_tenant_specific_key(
                    "get_user_by_oidc_settings.user_info_groups_key",
                    tenant,
                    "groups",
                ),
                [],
            )

        if config.get("_global_.auth.set_auth_cookie", True):
            expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                minutes=config.get_tenant_specific_key(
                    "jwt.expiration_minutes", tenant, 1200
                )
            )
            encoded_cookie = await generate_jwt_token(
                email,
                groups,
                tenant,
                roles=list(role_allowances),
                exp=expiration,
                mfa_setup_required=mfa_setup_required,
            )
            request.set_cookie(
                config.get("_global_.auth.cookie.name", "noq_auth"),
                encoded_cookie,
                expires=expiration,
                secure=config.get_tenant_specific_key(
                    "auth.cookie.secure",
                    tenant,
                    "https://" in config.get_tenant_specific_key("url", tenant),
                ),
                httponly=config.get_tenant_specific_key(
                    "auth.cookie.httponly", tenant, True
                ),
                samesite=config.get_tenant_specific_key(
                    "auth.cookie.samesite", tenant, True
                ),
            )

        if force_redirect:
            request.redirect(after_redirect_uri)
        else:
            if not return_200:
                # GraphQL (New UI) will not work if we return 403
                request.set_status(403)
            request.write(
                {
                    "type": "redirect",
                    "redirect_url": after_redirect_uri,
                    "reason": "unauthenticated",
                    "message": "User has been authenticated and needs to be redirected to their intended destination",
                }
            )
        await maybe_create_users_groups_in_database(
            request.ctx.db_tenant,
            email,
            groups,
            description="Created by SSO Sign-In",
            managed_by="SSO",
        )
        raise tornado.web.Finish()

    except Exception as e:
        log_data["error"] = e
        log.error(log_data, exc_info=True)
        return
