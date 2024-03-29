"""Handle the base."""
import asyncio
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import pytz
import redis
import sentry_sdk
import tornado.httpclient
import tornado.httputil
import tornado.web
from furl import furl
from tornado import httputil

import common.lib.noq_json as json
from common import User
from common.aws.role_access.utils import get_user_eligible_roles
from common.config import config
from common.config.tenant_config import TenantConfig
from common.exceptions.exceptions import (
    InvalidCertificateException,
    MissingCertificateException,
    MissingConfigurationValue,
    NoGroupsException,
    NoUserException,
    WebAuthNError,
)
from common.lib.alb_auth import authenticate_user_by_alb_auth
from common.lib.auth import AuthenticationError, is_tenant_admin
from common.lib.dynamo import UserDynamoHandler
from common.lib.jwt import (
    JwtAuthType,
    generate_jwt_token,
    validate_and_return_jwt_token,
)
from common.lib.oidc import authenticate_user_by_oidc
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.request_context.models import RequestContext
from common.lib.saml import authenticate_user_by_saml
from common.lib.tenant.models import TenantDetails
from common.lib.tenant.utils import is_tenant_active
from common.lib.tracing import ConsoleMeTracer
from common.lib.web import handle_generic_error_response
from common.lib.workos import WorkOS
from common.models import WebResponse
from common.tenants.models import Tenant

log = config.get_logger(__name__)


def maybe_set_security_headers(req):
    """
    Set security header if the request is coming from HTTPS and we're not in development
    """
    if "https://" not in req.request.headers.get("Referer", ""):
        return
    if config.get("_global_.development"):
        return
    # Require HTTPS for all requests to this domain in the user's browser
    # moving forward, until the expiration date.
    req.set_header("Strict-Transport-Security", "max-age=31536000; includeSubdomains")
    # Prevent other websites from embedding this site in an iframe.
    req.set_header("X-FRAME-OPTIONS", "Deny")
    # Prevents the browser from trying to guess (“sniff”) the MIME type, which can have security implications.
    req.set_header("X-XSS-Protection", "1; mode=block")
    # Prevents the browser from MIME-sniffing a response away from the declared content-type.
    req.set_header("X-Content-Type-Options", "nosniff")


class TornadoRequestHandler(tornado.web.RequestHandler):
    allowed_methods = ["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE", "OPTIONS"]

    def set_default_headers(self, *args, **kwargs):
        if config.get("_global_.development") and config.get(
            "_global_._development_disable_cors"
        ):
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Vary", "Origin")
            self.set_header(
                "Access-Control-Allow-Methods", ",".join(self.allowed_methods)
            )
            self.set_header(
                "Access-Control-Allow-Headers",
                "x-requested-with,access-control-allow-origin,authorization,content-type",
            )
            self.set_header("Access-Control-Allow-Credentials", "true")
            self.set_header("Content-Type", "application/json")
        maybe_set_security_headers(self)

    async def prepare(self):
        unprotected_routes = [
            "/healthcheck",
            "/api/v3/tenant_registration",
            "/api/v3/slack/oauth_redirect",
            "/api/v3/slack/events",
            "/api/v3/github/callback/",
            "/api/v3/github/events/",
        ]
        landing_page_domains_unprotected_routes = [
            "/aws_marketplace",
            "/aws_marketplace/form_submission",
        ]
        tenant = self.get_tenant_name()
        # Ensure request is for a valid tenant
        if config.is_tenant_configured(tenant):
            self.ctx = RequestContext(
                tenant=tenant,
                request_uuid=str(uuid.uuid4()),
                uri=self.request.uri,
            )
            await self.maybe_set_db_fields()
            return

        # Ignore unprotected routes, like /healthcheck
        if self.request.path in unprotected_routes:
            return

        # ok to ignore landing pages unprotected routes if
        # this is on landing page domains
        if (
            self.request.host in config.get("_global_.landing_page_domains", [])
            and self.request.path in landing_page_domains_unprotected_routes
        ):
            return

        # Complain loudly that we don't have a configuration for the tenant. Instruct
        # frontend to redirect to main page
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "message": "Invalid tenant specified. Redirecting to main page",
            "tenant": tenant,
        }
        await log.adebug(log_data)
        self.set_status(406)
        self.write(
            {
                "type": "redirect",
                "redirect_url": "https://noq.dev",  # TODO: Make this URL configurable?
                "reason": "unauthenticated",
                "message": "Invalid tenant specified",
            }
        )
        raise tornado.web.Finish()

    def get_tenant_url(self):
        protocol = self.request.protocol
        if "https://" in self.request.headers.get("Referer", ""):
            protocol = "https"
        full_host = self.request.headers.get("X-Forwarded-Host")
        if not full_host:
            full_host = self.get_tenant()
        return furl(f"{protocol}://{full_host}/")

    def get_tenant(self):
        if config.get("_global_.development"):
            x_forwarded_host = self.request.headers.get(
                "X-Forwarded-Host"
            )  # Adding default of localhost for development only
            if x_forwarded_host:
                return x_forwarded_host.split(":")[0]

        return self.request.host

    def get_tenant_name(self):
        return self.get_tenant().split(":")[0].replace(".", "_")

    def get_request_ip(self):
        tenant = self.get_tenant_name()
        trusted_remote_ip_header = config.get_tenant_specific_key(
            "auth.remote_ip.trusted_remote_ip_header", tenant
        )
        if not trusted_remote_ip_header:
            trusted_remote_ip_header = config.get(
                "_global_.auth.remote_ip.trusted_remote_ip_header"
            )
        if trusted_remote_ip_header:
            return self.request.headers[trusted_remote_ip_header].split(",")[0]
        return self.request.remote_ip

    async def maybe_set_db_fields(self):
        if not config.get("_global_.environment") == "test":
            if not self.ctx.db_tenant:
                self.ctx.db_tenant = await Tenant.get_by_name(self.ctx.tenant)
            if not self.ctx.db_user and self.ctx.db_tenant:
                user = getattr(self, "user", None) or self.ctx.user
                self.ctx.db_user = await User.get_by_email(self.ctx.db_tenant, user)


class BaseJSONHandler(TornadoRequestHandler):
    # These methods are returned in OPTIONS requests.
    # Default methods can be overridden by setting this variable in child classes.
    allowed_methods = ["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"]

    def __init__(self, *args, **kwargs):
        self.jwt_validator = kwargs.pop("jwt_validator", None)
        self.auth_required = kwargs.pop("auth_required", True)
        if self.jwt_validator is None:
            raise TypeError("Missing required keyword arg jwt_validator")
        super().__init__(*args, **kwargs)

    def check_xsrf_cookie(self):
        # CSRF token is not needed since this is protected by raw OIDC tokens
        pass

    def options(self, *args):
        self.set_header(
            "Access-Control-Allow-Headers",
            self.request.headers["Access-Control-Request-Headers"],
        )
        self.set_header("Content-Length", "0")
        self.set_status(204)
        self.finish()

    async def prepare(self):
        tenant = self.get_tenant_name()
        if not config.is_tenant_configured(tenant):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid tenant specified. Redirecting to main page",
                "tenant": tenant,
            }
            await log.adebug(log_data)
            self.set_status(406)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid tenant specified",
                }
            )
            raise tornado.web.Finish()
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        stats.timer("base_handler.incoming_request")
        if self.request.method.lower() == "options":
            return
        self.request_uuid = str(uuid.uuid4())
        payload = self.get_current_user()
        self.auth_context = payload
        self.user = payload["email"]

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "application/problem+json")
        title = httputil.responses.get(status_code, "Unknown")
        message = kwargs.get("message", self._reason)
        # self.set_status() modifies self._reason, so this call should come after we grab the reason
        self.set_status(status_code)
        self.write(
            json.dumps(
                {"status": status_code, "title": title, "message": message}
            )  # noqa
        )
        raise tornado.web.Finish()

    def get_current_user(self):
        tenant = self.get_tenant_name()
        try:
            if config.get("_global_.development") and config.get_tenant_specific_key(
                "json_authentication_override", tenant
            ):
                return config.get_tenant_specific_key(
                    "json_authentication_override", tenant
                )
            tkn_header = self.request.headers["authorization"]
        except KeyError:
            raise WebAuthNError(reason="Missing Authorization Header")
        else:
            tkn_str = tkn_header.split(" ")[-1]
        try:
            tkn = self.jwt_validator(tkn_str)
        except AuthenticationError as e:
            raise WebAuthNError(reason=e.message)
        else:
            return tkn


class BaseHandler(TornadoRequestHandler):
    """Default BaseHandler."""

    def log_exception(self, *args, **kwargs):
        if args[0].__name__ == "Finish":
            pass
        else:
            super(BaseHandler, self).log_exception(*args, **kwargs)

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        tenant = self.get_tenant_name()
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            raise tornado.web.Finish()
        else:
            self.write(
                "<html><title>%(code)d: %(message)s</title>"
                "<body>%(code)d: %(message)s</body></html>"
                % {
                    "code": status_code,
                    "message": f"{self._reason} - {config.get_tenant_specific_key('errors.custom_website_error_message', tenant, '')}",
                }
            )
            raise tornado.web.Finish()

    def data_received(self, chunk):
        """Receives the data."""

    def initialize(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.tracer = None
        self.responses = []
        self.ctx: Union[None, RequestContext] = None
        super(BaseHandler, self).initialize()

    async def prepare(self) -> None:
        await super(BaseHandler, self).prepare()
        tenant = self.get_tenant_name()
        if not config.is_tenant_configured(tenant):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid tenant specified. Redirecting to main page",
                "tenant": tenant,
            }
            await log.adebug(log_data)
            self.set_status(406)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid tenant specified",
                }
            )
            raise tornado.web.Finish()
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        self.tracer = None

        await self.configure_tracing()

        if config.get("_global_.tornado.xsrf", True):
            cookie_kwargs = config.get("_global_.tornado.xsrf_cookie_kwargs", {})
            self.set_cookie(
                config.get("_global_.xsrf_cookie_name", "_xsrf"),
                self.xsrf_token,
                **cookie_kwargs,
            )
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        return await self.authorization_flow()

    async def configure_tracing(self):
        tenant = self.get_tenant_name()
        self.tracer = ConsoleMeTracer()
        primary_span_name = "{0} {1}".format(
            self.request.method.upper(), self.request.path
        )
        tracer_tags = {
            "http.host": config.hostname,
            "http.method": self.request.method.upper(),
            "http.path": self.request.path,
            "ca": self.get_request_ip(),  # Client IP
            "http.url": self.request.full_url(),
        }
        tracer = await self.tracer.configure_tracing(
            primary_span_name, tenant, tags=tracer_tags
        )
        if tracer:
            for k, v in tracer.headers.items():
                self.set_header(k, v)

    def on_finish(self) -> None:
        # tenant = self.get_tenant_name()
        if hasattr(self, "tracer") and self.tracer:
            asyncio.ensure_future(
                self.tracer.set_additional_tags({"http.status_code": self.get_status()})
            )
            asyncio.ensure_future(self.tracer.finish_spans())
            asyncio.ensure_future(self.tracer.disable_tracing())

        super(BaseHandler, self).on_finish()

    async def attempt_sso_authn(self, tenant) -> bool:
        """
        Noq's configuration allows authenticating users by user/password, SSO, or both.
        This function helps determine how Noq should authenticate a user. If user/password login is allowed,
        users will be redirected to Noq's login page (/login). If SSO is also allowed, the Login page will present
        a button allowing the user to sign in with SSO.

        If user/password login is enabled, we don't want to give users the extra step of having to visit the login page,
        so we just authenticate them through SSO directly.
         allow authenticating users by a combination of user/password and SSO. In this case, we need to tell
        Returns: boolean
        """
        if not config.get_tenant_specific_key(
            "auth.get_user_by_password", tenant, False
        ):
            return True

        # force_use_sso indicates the user's intent to authenticate via SSO
        force_use_sso = self.request.arguments.get("use_sso", [False])[0]
        if force_use_sso:
            return True
        # It's a redirect from an SSO provider. Let it hit the SSO functionality
        if (
            "code" in self.request.query_arguments
            and "state" in self.request.query_arguments
        ):
            return True
        if self.request.path == "/saml/acs":
            return True
        return False

    async def authorization_flow(
        self,
        user: Optional[str] = None,
        console_only: bool = True,
        refresh_cache: bool = False,
        jwt_tokens: Optional[Dict[str, str]] = None,
        jwt_auth_type: Optional[JwtAuthType] = None,
    ) -> None:
        """Perform high level authorization flow."""
        # TODO: Prevent any sites being created with a subdomain that is a yaml keyword, ie: false, no, yes, true, etc
        # TODO: Return Authentication prompt regardless of subdomain
        # TODO: When it fails, all the process got truncated. e.g. when saml setting is enabled but idp_metadata_url is not correct.

        tenant = self.get_tenant_name()
        tenant_config = TenantConfig.get_instance(tenant)
        self.eula_signed = None
        self.tenant_active = None
        self.mfa_setup_required = None
        self.password_reset_required = None
        self.mfa_verification_required = None
        self.sso_user = None
        self.eligible_roles = []
        self.user_role_name = None
        self.eligible_accounts = []
        self.request_uuid = str(uuid.uuid4())
        sso_signin_toggle = self.request.query_arguments.get("sso_signin") == [b"true"]

        group_mapping = get_plugin_by_name(
            config.get_tenant_specific_key(
                "plugins.group_mapping",
                tenant,
                "cmsaas_group_mapping",
            )
        )()
        auth = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
        )()
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        refresh_cache = (
            self.request.arguments.get("refresh_cache", [False])[0] or refresh_cache
        )

        attempt_sso_authn = await self.attempt_sso_authn(tenant)

        refreshed_user_roles_from_cache = False

        if not refresh_cache and config.get(
            "_global_.role_cache.always_refresh_roles_cache", False
        ):
            refresh_cache = True

        self.ip = self.get_request_ip()
        self.user = user
        self.groups = None
        self.user_role_name = None
        self.auth_cookie_expiration = 0
        log_data = {
            "function": "Basehandler.authorization_flow",
            "ip": self.ip,
            "request_path": self.request.uri,
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "message": "Incoming request",
            "tenant": tenant,
        }
        await log.adebug(log_data)

        # Check to see if user has a valid auth cookie
        auth_cookie = self.get_cookie(self.get_noq_auth_cookie_key())

        # Validate auth cookie and use it to retrieve group information
        if auth_cookie:
            # Is this slow?
            res = await validate_and_return_jwt_token(auth_cookie, tenant)
            if isinstance(res, dict):
                self.user = res.get("user")
                # Add groups_pending_eula so authorization_flow works as expected
                # If EULA isn't signed groups will be cleared at the end of the auth flow
                self.groups = res.get("groups", []) + res.get("groups_pending_eula", [])
                self.eligible_roles = res.get("additional_roles", [])
                self.auth_cookie_expiration = res.get("exp")
                self.eula_signed = res.get("eula_signed", False)
                self.tenant_active = res.get("tenant_active", False)
                self.mfa_setup_required = res.get("mfa_setup_required", None)
                self.mfa_verification_required = res.get(
                    "mfa_verification_required", None
                )
                self.password_reset_required = res.get("password_reset_required", False)
                self.sso_user = res.get("sso_user", False)

        # if tenant in ["localhost", "127.0.0.1"] and not self.user:
        # Check for development mode and a configuration override that specify the user and their groups.
        if (
            not self.user
            and config.get("_global_.development")
            and config.get_tenant_specific_key("_development_user_override", tenant)
        ):
            self.user = config.get_tenant_specific_key(
                "_development_user_override", tenant
            )

        if not self.user and sso_signin_toggle:
            # Redirect to SSO provider
            if config.get_tenant_specific_key("auth.get_user_by_saml", tenant, False):
                res = await authenticate_user_by_saml(
                    self, return_200=True, force_redirect=False
                )
                if not res:
                    if (
                        self.request.uri != "/saml/acs"
                        and not self.request.uri.startswith("/auth?")
                    ):
                        raise tornado.web.Finish(
                            "Unable to authenticate the user by SAML. "
                            "Redirecting to authentication endpoint"
                        )
                    return
            if (
                config.get_tenant_specific_key("auth.get_user_by_oidc", tenant, False)
                and attempt_sso_authn
            ):
                res = await authenticate_user_by_oidc(
                    self, return_200=True, force_redirect=False
                )
                if not res:
                    raise tornado.web.Finish(
                        "Unable to authenticate the user by OIDC. "
                        "Redirecting to authentication endpoint"
                    )
                elif isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        # Legacy auth stll needed while we have the old UI
        if not self.user:
            # Authenticate user by API Key
            if config.get_tenant_specific_key(
                "auth.get_user_by_api_key", tenant, False
            ):
                api_key = self.request.headers.get("X-API-Key")
                api_user = self.request.headers.get("X-API-User")
                if bool(api_key) != bool(api_user):
                    raise Exception(
                        "X-API-Key and X-API-User must be both present or both absent"
                    )
                if api_key and api_user:
                    ddb = UserDynamoHandler(tenant)
                    self.user = await ddb.verify_api_key(api_key, api_user, tenant)

        if not self.user:
            if tenant_config.auth_get_user_by_workos and attempt_sso_authn:
                workos = WorkOS(tenant)
                res = await workos.authenticate_user_by_workos(self)
                if not res:
                    raise tornado.web.Finish(
                        "Unable to authenticate the user by WorkOS OIDC. "
                        "Redirecting to authentication endpoint"
                    )
                elif isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")
        if not self.user:
            # SAML flow. If user has a JWT signed by Noq, and SAML is enabled in configuration, user will go
            # through this flow.

            if (
                config.get_tenant_specific_key("auth.get_user_by_saml", tenant, False)
                and attempt_sso_authn
            ):
                res = await authenticate_user_by_saml(self)
                if not res:
                    if (
                        self.request.uri != "/saml/acs"
                        and not self.request.uri.startswith("/auth?")
                    ):
                        raise tornado.web.Finish(
                            "Unable to authenticate the user by SAML. "
                            "Redirecting to authentication endpoint"
                        )
                    return

        if not self.user:
            if (
                config.get_tenant_specific_key("auth.get_user_by_oidc", tenant, False)
                and attempt_sso_authn
            ):
                res = await authenticate_user_by_oidc(self)
                if not res:
                    raise tornado.web.Finish(
                        "Unable to authenticate the user by OIDC. "
                        "Redirecting to authentication endpoint"
                    )
                elif isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            if config.get_tenant_specific_key(
                "auth.get_user_by_aws_alb_auth", tenant, False
            ):
                res = await authenticate_user_by_alb_auth(self)
                if not res:
                    raise Exception("Unable to authenticate the user by ALB Auth")
                elif isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            # Username/Password authn flow
            if config.get_tenant_specific_key(
                "auth.get_user_by_password", tenant, False
            ):
                after_redirect_uri = self.request.arguments.get("redirect_url", [""])[0]
                if after_redirect_uri and isinstance(after_redirect_uri, bytes):
                    after_redirect_uri = after_redirect_uri.decode("utf-8")
                self.set_status(403)
                self.write(
                    {
                        "type": "redirect",
                        "redirect_url": f"/login?redirect_after_auth={after_redirect_uri}",
                        "reason": "unauthenticated",
                        "message": "User is not authenticated. Redirect to authenticate",
                    }
                )
                await self.finish()
                raise tornado.web.Finish(
                    "Redirecting user to authenticate by username/password."
                )

        if not self.user:
            try:
                # Get user. Config options can specify getting username from headers or
                # OIDC, but custom plugins are also allowed to override this.
                try:
                    self.user = await auth.get_user(self)
                except Exception:
                    sentry_sdk.capture_exception()
                    self.user = None
                if not self.user:
                    raise NoUserException(
                        f"User not detected. Headers: {self.request.headers}"
                    )
                log_data["user"] = self.user
            except NoUserException:
                self.clear()
                self.set_status(403)

                stats.count(
                    "Basehandler.authorization_flow.no_user_detected",
                    tags={
                        "request_path": self.request.uri,
                        "ip": self.ip,
                        "user_agent": self.request.headers.get("User-Agent"),
                        "tenant": tenant,
                    },
                )
                log_data["message"] = "No user detected. Please login first."
                await log.aerror(log_data)
                self.write(log_data["message"])
                raise tornado.web.Finish()
        log_data["user"] = self.user

        if not self.eula_signed:
            try:
                tenant_details = await TenantDetails.get(tenant)
                self.eula_signed = bool(tenant_details.eula_info)
            except Exception:
                # TODO: Move this along with other tenant validator checks into dedicated method.
                #   Also, this should redirect to a sign-up page per https://perimy.atlassian.net/browse/EN-930
                self.eula_signed = False

            # This is also our chance to validate subscription status
            if not tenant_details:
                self.write(
                    f"Tenant {tenant} was not found. Please contact your administrator. "
                    "If you are an administrator, please confirm your subscription status in "
                    "Amazon Marketplace."
                )
                raise tornado.web.Finish(
                    f"Tenant {tenant} not found. Please contact your administrator."
                )
            # We take advantage of the eula request that we're already performing to also check
            # tenant status. If the tenant is not active, we'll return a 401. This is so we're not
            # querying the database for every single user/request, and we don't have to have
            # complex caching logic in place. This also means that tenants will be "expired"
            # after all JWTs have expired (By default, every 6 hours)
        if not self.tenant_active:
            self.tenant_active = await is_tenant_active(tenant)

            if not self.tenant_active:
                tenant_not_active_message = (
                    "Your tenant is not active. Please contact your administrator or the Noq team. "
                    "If you are an administrator, please confirm your subscription status in "
                    "Amazon Marketplace."
                )
                self.set_status(401)
                self.write(
                    WebResponse(
                        status="error",
                        status_code=401,
                        data={"message": tenant_not_active_message},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                log.error(
                    tenant_not_active_message,
                    tenant=tenant,
                )
                raise tornado.web.Finish()

        self.contractor = False  # TODO: Add functionality later for contractor detection via regex or something else

        if (
            config.get_tenant_specific_key(
                "auth.cache_user_info_server_side", tenant, True
            )
            and not refresh_cache
        ):
            try:
                red = await RedisHandler().redis(tenant)
                cache_r = red.get(f"{tenant}_USER-{self.user}-CONSOLE-{console_only}")
            except (
                redis.exceptions.ConnectionError,
                redis.exceptions.ClusterDownError,
            ):
                cache_r = None
            if cache_r:
                log_data["message"] = "Loading from cache"
                await log.adebug(log_data)
                cache = json.loads(cache_r)
                self.groups = cache.get("groups", [])
                self.eligible_roles = cache.get("eligible_roles", [])
                self.eligible_accounts = cache.get("eligible_accounts")
                self.user_role_name = cache.get("user_role_name")
                refreshed_user_roles_from_cache = True
        if not refreshed_user_roles_from_cache:
            await self.set_groups()

        self.is_admin = is_tenant_admin(self.user, self.groups, tenant)
        self.console_only = console_only

        if (
            not self.eligible_accounts
            and self.eula_signed
            and self.tenant_active
            and not self.mfa_setup_required
        ):
            try:
                self.eligible_accounts = await group_mapping.get_eligible_accounts(
                    tenant, self.eligible_roles
                )
                log_data["eligible_accounts"] = len(self.eligible_accounts)
                log_data["message"] = "Successfully authorized user."
                await log.adebug(log_data)
            except Exception:
                stats.count("Basehandler.authorization_flow.exception")
                await log.aerror(log_data, exc_info=True)
                raise
        if (
            config.get_tenant_specific_key(
                "auth.cache_user_info_server_side", tenant, True
            )
            and self.groups
            # Only set role cache if we didn't retrieve user's existing roles from cache
            and not refreshed_user_roles_from_cache
        ):
            try:
                red = await RedisHandler().redis(tenant)
                red.setex(
                    f"{tenant}_USER-{self.user}-CONSOLE-{console_only}",
                    config.get_tenant_specific_key(
                        "role_cache.cache_expiration", tenant, 60
                    ),
                    json.dumps(
                        {
                            "groups": self.groups,
                            "eligible_roles": self.eligible_roles,
                            "eligible_accounts": self.eligible_accounts,
                            "user_role_name": self.user_role_name,
                        }
                    ),
                )
            except (
                redis.exceptions.ConnectionError,
                redis.exceptions.ClusterDownError,
            ):
                pass
        if not self.get_cookie(self.get_noq_auth_cookie_key()):
            await self.set_jwt_cookie(tenant)

        if hasattr(self, "tracer") and self.tracer:
            await self.tracer.set_additional_tags({"USER": self.user})
        stats.timer(
            "base_handler.incoming_request",
            {
                "user": self.user,
                "tenant": tenant,
                "uri": self.request.uri,
                "method": self.request.method,
            },
        )

        if self.__class__.__name__ == "UserProfileHandler":
            # Let the user profile endpoint through
            pass
        elif not self.tenant_active:
            # Tenant is inactive in Global tenant_details DynamoDB Table.
            # Possibly unsubscribed in AWS Marketplace.
            self.set_status(403)
            self.write(
                WebResponse(
                    status_code=403,
                    reason="Tenant is not active",
                    data={"message": "TENANT_INACTIVE"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        elif (
            self.password_reset_required
            or self.__class__.__name__ == "PasswordResetSelfServiceHandler"
        ):
            # If the EULA hasn't been signed the user cannot access any AWS information.

            if self.__class__.__name__ not in [
                "PasswordResetSelfServiceHandler",
                "AuthenticatedStaticFileHandler",
            ]:
                self.write(
                    {
                        "type": "redirect",
                        "redirect_url": "/reset_password",
                        "reason": "unauthenticated",
                        "message": "PASSWORD_RESET_REQUIRED",
                    }
                )
                self.set_status(403)
                raise tornado.web.Finish()
        elif self.mfa_setup_required and tenant_config.require_mfa:
            # If the EULA hasn't been signed the user cannot access any AWS information.

            if self.__class__.__name__ not in [
                "CognitoUserSetupMFA",
                "UserMFASelfServiceHandler",
                "AuthenticatedStaticFileHandler",
            ]:
                self.write(
                    {
                        "type": "redirect",
                        "redirect_url": "/mfa",
                        "reason": "unauthenticated",
                        "message": "MFA_SETUP_REQUIRED",
                    }
                )
                self.set_status(403)
                raise tornado.web.Finish()
        elif self.mfa_verification_required and self.__class__.__name__ not in [
            "MfaHandler",
            "AuthenticatedStaticFileHandler",
        ]:
            self.write(
                WebResponse(
                    status_code=403,
                    reason="MFA verification required",
                    data={"message": "MFA_VERIFICATION_REQUIRED"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        elif not self.eula_signed:
            await self.maybe_set_db_fields()
            self.ctx = RequestContext(
                tenant=tenant,
                db_tenant=self.ctx.db_tenant,
                user=self.user,
                db_user=self.ctx.db_user,
                groups=self.groups,
                request_uuid=self.request_uuid,
                uri=self.request.uri,
                mfa_setup_required=self.mfa_setup_required,
                password_reset_required=self.password_reset_required,
                needs_to_sign_eula=not self.eula_signed,
                mfa_verification_required=self.mfa_verification_required,
                is_admin=self.is_admin,
            )

            if self.__class__.__name__ not in [
                "TenantEulaHandler",
                "AuthenticatedStaticFileHandler",
                "MfaHandler",
                "UserMFASelfServiceHandler",
            ]:
                # Force them to the eula page if they're an admin, return a 403 otherwise
                if self.is_admin:
                    self.write(
                        {
                            "type": "redirect",
                            "redirect_url": "/eula",
                            "reason": "unauthenticated",
                            "message": "EULA_NOT_SIGNED",
                        }
                    )
                else:
                    self.write(
                        WebResponse(
                            status_code=403,
                            reason="The EULA for this tenant has not been signed. Please contact your admin.",
                        ).json(exclude_unset=True, exclude_none=True)
                    )

                self.set_status(403)
                raise tornado.web.Finish()

        await self.maybe_set_db_fields()
        self.ctx = RequestContext(
            tenant=tenant,
            db_tenant=self.ctx.db_tenant,
            user=self.user,
            db_user=self.ctx.db_user,
            groups=self.groups,
            request_uuid=self.request_uuid,
            uri=self.request.uri,
            mfa_setup_required=self.mfa_setup_required,
            password_reset_required=self.password_reset_required,
            needs_to_sign_eula=not self.eula_signed,
            mfa_verification_required=self.mfa_verification_required,
            is_admin=self.is_admin,
        )

    async def set_groups(self):
        tenant = self.get_tenant_name()

        if (
            not self.groups
            and config.get("_global_.development")
            and config.get_tenant_specific_key("_development_groups_override", tenant)
        ):
            self.groups = config.get_tenant_specific_key(
                "_development_groups_override", tenant
            )
            return

        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        auth = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
        )()

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "tenant": tenant,
        }
        try:
            try:
                self.groups = await auth.get_groups(
                    self.groups, self.user, self, headers=self.request.headers
                )
            except Exception as e:
                await log.aerror(
                    {
                        **log_data,
                        "error": str(e),
                        "message": "Unable to get groups",
                    },
                    exc_info=True,
                )
                sentry_sdk.capture_exception()
            if not self.groups:
                raise NoGroupsException(f"Groups not detected for {self.user}.")

        except NoGroupsException:
            stats.count("Basehandler.authorization_flow.no_groups_detected")
            log_data[
                "message"
            ] = "No groups detected for user. Check configuration. Letting user continue."
            await log.awarning(log_data)

    async def extend_eligible_roles(self, console_only: bool = False):
        await self.maybe_set_db_fields()
        eligible_roles = await get_user_eligible_roles(
            self.ctx.db_tenant, self.ctx.db_user, self.groups
        )
        await log.awarning(
            "Retrieved eligible roles for user",
            user=self.ctx.db_user.email,
            groups=self.groups,
            eligible_roles=eligible_roles,
        )
        self.eligible_roles = list(set(eligible_roles + self.eligible_roles))

    async def clear_jwt_cookie(self):
        cookie_name = self.get_noq_auth_cookie_key()
        self.clear_cookie(cookie_name)

    async def set_jwt_cookie(self, tenant, roles: list = None):
        expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
            minutes=config.get_tenant_specific_key(
                "jwt.expiration_minutes", tenant, 1200
            )
        )

        encoded_cookie = await generate_jwt_token(
            self.user,
            self.groups,
            tenant,
            roles,
            exp=expiration,
            eula_signed=self.eula_signed,
            tenant_active=self.tenant_active,
            mfa_setup_required=self.mfa_setup_required,
        )
        self.set_cookie(
            self.get_noq_auth_cookie_key(),
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

    async def fte_check(self):
        if (
            config.get_tenant_specific_key(
                "policy_editor.disallow_contractors", self.ctx.tenant, True
            )
            and self.contractor
        ):
            if self.user not in config.get_tenant_specific_key(
                "groups.can_bypass_contractor_restrictions",
                self.ctx.tenant,
                [],
            ):
                self.set_status(403)
                self.write(
                    {
                        "code": "403",
                        "message": "Only Full-Time Employees are allowed access to make this request.",
                    }
                )
                raise tornado.web.Finish()

    @classmethod
    def get_noq_auth_cookie_key(cls):
        attr_name = "noq_auth_cookie_key"
        if cookie_key := getattr(cls, attr_name, None):
            return cookie_key

        cookie_key = config.get("_global_.auth.cookie.name", "noq_auth")
        setattr(cls, attr_name, cookie_key)
        return cookie_key


class BaseAPIV1Handler(BaseHandler):
    """Default API Handler for api/v1/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")
        super().set_default_headers()


class BaseAPIV2Handler(BaseHandler):
    """Default API Handler for api/v2/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")
        super().set_default_headers()

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            self.set_status(status_code)
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            raise tornado.web.Finish()
        else:
            self.set_header("Content-Type", "application/problem+json")
            title = httputil.responses.get(status_code, "Unknown")
            message = kwargs.get("message", self._reason)
            # self.set_status() modifies self._reason, so this call should come after we grab the reason
            self.set_status(status_code)
            self.write(
                json.dumps(
                    {"status": status_code, "title": title, "message": message}
                )  # noqa
            )
            raise tornado.web.Finish()


class BaseMtlsHandler(BaseAPIV2Handler):
    def initialize(self, **kwargs):
        self.kwargs = kwargs

    async def prepare(self):
        self.tracer = None
        self.span = None
        self.spans = {}
        self.responses = []
        self.request_uuid = str(uuid.uuid4())
        self.auth_cookie_expiration = 0
        self.password_reset_required = False
        self.user_role_name = None
        tenant = self.get_tenant_name()
        self.ctx = RequestContext(
            tenant=tenant,
            request_uuid=self.request_uuid,
            uri=self.request.uri,
        )
        if not config.is_tenant_configured(tenant):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid tenant specified. Redirecting to main page",
                "tenant": tenant,
            }
            await log.adebug(log_data)
            self.set_status(406)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid tenant specified",
                }
            )
            await self.finish()
            raise tornado.web.Finish(log_data["message"])
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        stats.timer("base_handler.incoming_request")
        auth = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.auth", tenant, "cmsaas_auth")
        )()
        if config.get_tenant_specific_key("auth.require_mtls", tenant, False):
            try:
                await auth.validate_certificate(self)
            except InvalidCertificateException:
                stats.count(
                    "GetCredentialsHandler.post.invalid_certificate_header_value"
                )
                self.set_status(403)
                self.write({"code": "403", "message": "Invalid Certificate"})
                raise tornado.web.Finish()

            # Extract user from valid certificate
            try:
                self.requester = await auth.extract_user_from_certificate(
                    self.request.headers
                )
                self.current_cert_age = await auth.get_cert_age_seconds(
                    self.request.headers
                )
            except (MissingCertificateException, Exception) as e:
                if isinstance(e, MissingCertificateException):
                    stats.count("BaseMtlsHandler.post.missing_certificate_header")
                    message = "Missing Certificate in Header."
                else:
                    stats.count("BaseMtlsHandler.post.exception")
                    message = f"Invalid Mtls Certificate: {e}"
                self.set_status(400)
                self.write({"code": "400", "message": message})
                raise tornado.web.Finish()
        elif config.get_tenant_specific_key("auth.require_jwt", tenant, True):
            auth_cookie = self.get_cookie(self.get_noq_auth_cookie_key())

            if auth_cookie:
                res = await validate_and_return_jwt_token(auth_cookie, tenant)
                if not res:
                    error = {
                        "code": "invalid_jwt",
                        "message": "JWT is invalid or has expired.",
                        "request_id": self.request_uuid,
                    }
                    self.set_status(403)
                    self.write(error)
                    raise tornado.web.Finish()
                self.user = res.get("user")
                self.groups = res.get("groups")
                self.eligible_roles += res.get("additional_roles")
                await self.extend_eligible_roles()
                self.eligible_roles = list(set(self.eligible_roles))
                self.password_reset_required = res.get("password_reset_required")
                self.sso_user = res.get("sso_user")
                self.requester = {"type": "user", "email": self.user}
                self.current_cert_age = int(time.time()) - res.get("iat")
                self.auth_cookie_expiration = res.get("exp")
                stats.timer(
                    "base_handler.incoming_request",
                    {
                        "user": self.user,
                        "tenant": tenant,
                        "uri": self.request.uri,
                        "method": self.request.method,
                    },
                )
                self.ctx = RequestContext(
                    tenant=tenant,
                    user=self.user,
                    groups=self.groups,
                    request_uuid=self.request_uuid,
                    uri=self.request.uri,
                )
            else:
                raise MissingConfigurationValue(
                    "Auth cookie name is not defined in configuration."
                )
        else:
            raise MissingConfigurationValue("Unsupported authentication scheme.")
        if not hasattr(self, "requester"):
            raise tornado.web.HTTPError(403, "Unable to authenticate user.")
        self.ip = self.get_request_ip()
        await self.configure_tracing()

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        # tenant = self.get_tenant_name()
        # if config.get_tenant_specific_key(
        #     "_security_risk_full_debugging.enabled", tenant
        # ):
        #     self.responses.append(chunk)
        super(BaseMtlsHandler, self).write(chunk)

    def on_finish(self) -> None:
        # tenant = self.get_tenant_name()
        # if config.get_tenant_specific_key(
        #     "_security_risk_full_debugging.enabled", tenant
        # ):
        #     request_details = {
        #         "path": self.request.path,
        #         "method": self.request.method,
        #         "body": self.request.body,
        #         "arguments": self.request.arguments,
        #         "body_arguments": self.request.body_arguments,
        #         "headers": dict(self.request.headers.items()),
        #         "query": self.request.query,
        #         "query_arguments": self.request.query_arguments,
        #         "uri": self.request.uri,
        #         "cookies": dict(self.request.cookies.items()),
        #         "response": self.responses,
        #     }
        #     with open(
        #         config.get_tenant_specific_key(
        #             "_security_risk_full_debugging.file", tenant
        #         ),
        #         "a+",
        #     ) as f:
        #         f.write(json.dumps(request_details, reject_bytes=False))
        super(BaseMtlsHandler, self).on_finish()


class NoCacheStaticFileHandler(tornado.web.StaticFileHandler):
    def set_default_headers(self) -> None:
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )
        maybe_set_security_headers(self)


class StaticFileHandler(tornado.web.StaticFileHandler):
    def initialize(self, **kwargs) -> None:
        super(StaticFileHandler, self).initialize(**kwargs)

    def log_exception(self, typ, value, tb):
        if isinstance(value, tornado.web.Finish):
            # if Finish is raised, we want to ignore it.
            return
        super(StaticFileHandler, self).log_exception(typ, value, tb)

    def get_tenant(self):
        if config.get("_global_.development"):
            x_forwarded_host = self.request.headers.get("X-Forwarded-Host", "")
            if x_forwarded_host:
                return x_forwarded_host.split(":")[0]

        return self.request.host

    def get_tenant_name(self):
        return self.get_tenant().split(":")[0].replace(".", "_")

    async def prepare(self, **kwargs) -> None:
        tenant = self.get_tenant_name()
        if not config.is_tenant_configured(tenant):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid tenant specified. Redirecting to main page",
                "tenant": tenant,
            }
            await log.adebug(log_data)
            self.set_status(418)
            raise tornado.web.Finish()
        self.ctx = RequestContext(
            tenant=tenant,
            user=None,
            request_uuid=str(uuid.uuid4()),
            uri=self.request.uri,
        )
        super(StaticFileHandler, self).prepare(**kwargs)


class AuthenticatedStaticFileHandler(tornado.web.StaticFileHandler, BaseHandler):
    def initialize(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.tracer = None
        self.responses = []
        self.ctx: Union[None, RequestContext] = None
        super(AuthenticatedStaticFileHandler, self).initialize(**kwargs)

    async def prepare(self) -> None:
        await super(AuthenticatedStaticFileHandler, self).prepare()

    async def get(self, path: str, include_body: bool = True) -> None:
        await super(AuthenticatedStaticFileHandler, self).get(path, include_body)


class BaseAdminHandler(BaseHandler):
    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")
        super(BaseAdminHandler, self).set_default_headers()

    async def authorization_flow(
        self,
        user: str = None,
        console_only: bool = True,
        refresh_cache: bool = False,
        jwt_tokens: Optional[Dict[str, str]] = None,
        jwt_auth_type: JwtAuthType = None,
    ) -> None:
        await super(BaseAdminHandler, self).authorization_flow(
            user,
            console_only,
            refresh_cache,
            jwt_tokens,
            jwt_auth_type,
        )

        if not getattr(self.ctx, "tenant") or not self.is_admin:
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, errors[0], errors, 403, "unauthorized", {}
            )
            raise tornado.web.Finish()


class ScimAuthHandler(TornadoRequestHandler):
    """
    This handler is used to authenticate SCIM requests.
    It should only be used by Identity Providers, and not by end users.
    """

    def initialize(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.tracer = None
        self.responses = []
        self.ctx: Union[None, RequestContext] = None
        super(ScimAuthHandler, self).initialize(**kwargs)

    async def prepare(self) -> None:
        await super(ScimAuthHandler, self).prepare()
        self.request_uuid: str = str(uuid.uuid4())
        tenant: str = self.get_tenant_name()
        tenant_config = TenantConfig.get_instance(tenant)
        if not tenant_config.scim_enabled:
            raise tornado.web.HTTPError(403, "SCIM not configured.")
        if not tenant_config.scim_bearer_token:
            raise tornado.web.HTTPError(403, "Bearer token not configured.")

        bearer_header: str = self.request.headers.get("Authorization", "")
        if not bearer_header:
            raise tornado.web.HTTPError(403, "Invalid bearer token.")
        authorization_token = bearer_header.replace("Bearer ", "").strip()

        if authorization_token != tenant_config.scim_bearer_token:
            raise tornado.web.HTTPError(403, "Invalid bearer token.")
