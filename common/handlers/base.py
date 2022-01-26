"""Handle the base."""
import asyncio
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any, Union

import pytz
import redis
import sentry_sdk
import tornado.httpclient
import tornado.httputil
import tornado.web
import ujson as json
from rediscluster.exceptions import ClusterDownError
from tornado import httputil

from common.config import config
from common.exceptions.exceptions import (
    InvalidCertificateException,
    MissingCertificateException,
    MissingConfigurationValue,
    NoGroupsException,
    NoUserException,
    SilentException,
    WebAuthNError,
)
from common.lib.alb_auth import authenticate_user_by_alb_auth
from common.lib.auth import AuthenticationError
from common.lib.dynamo import UserDynamoHandler
from common.lib.jwt import generate_jwt_token, validate_and_return_jwt_token
from common.lib.oidc import authenticate_user_by_oidc
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.request_context.models import RequestContext
from common.lib.saml import authenticate_user_by_saml
from common.lib.tracing import ConsoleMeTracer

log = config.get_logger()


class TornadoRequestHandler(tornado.web.RequestHandler):
    def prepare(self):
        unprotected_routes = ["/healthcheck", "/api/v3/tenant_registration"]
        host = self.get_host_name()
        # Ensure request is for a valid host / tenant
        if config.is_host_configured(host):
            return

        # Ignore unprotected routes, like /healthcheck
        if self.request.uri in unprotected_routes:
            return

        # Complain loudly that we don't have a configuration for the host/tenant. Instruct
        # frontend to redirect to main page
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "message": "Invalid host specified. Redirecting to main page",
        }
        log.debug(log_data)
        self.set_status(403)
        self.write(
            {
                "type": "redirect",
                "redirect_url": "https://noq.dev",  # TODO: Make this URL configurable?
                "reason": "unauthenticated",
                "message": "Invalid host specified",
            }
        )
        return

    def get_host(self):
        if config.get("_global_.development"):
            x_forwarded_host = self.request.headers.get("X-Forwarded-Host", "")
            if x_forwarded_host:
                return x_forwarded_host.split(":")[0]

        return self.request.host

    def get_host_name(self):
        return self.get_host().split(":")[0].replace(".", "_")

    def get_request_ip(self):
        host = self.get_host_name()
        trusted_remote_ip_header = config.get_host_specific_key(
            "auth.remote_ip.trusted_remote_ip_header", host
        )
        if trusted_remote_ip_header:
            return self.request.headers[trusted_remote_ip_header].split(",")[0]
        return self.request.remote_ip


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
        host = self.get_host_name()
        if not config.is_host_configured(host):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid host specified. Redirecting to main page",
            }
            log.debug(log_data)
            self.set_status(403)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid host specified",
                }
            )
            return
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

    # def set_default_headers(self, *args, **kwargs):
    #     self.set_header("Access-Control-Allow-Origin", "*")
    #     self.set_header("Access-Control-Allow-Methods", ",".join(self.allowed_methods))
    #     self.set_header("Access-Control-Allow-Credentials", "true")
    #     self.set_header("Content-Type", "application/json")

    def write_error(self, status_code, **kwargs):
        self.set_header("Content-Type", "application/problem+json")
        title = httputil.responses.get(status_code, "Unknown")
        message = kwargs.get("message", self._reason)
        # self.set_status() modifies self._reason, so this call should come after we grab the reason
        self.set_status(status_code)
        self.finish(
            json.dumps(
                {"status": status_code, "title": title, "message": message}
            )  # noqa
        )

    def get_current_user(self):
        host = self.get_host_name()
        try:
            if config.get_host_specific_key(
                "development", host
            ) and config.get_host_specific_key("json_authentication_override", host):
                return config.get_host_specific_key(
                    "json_authentication_override", host
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
        if args[0].__name__ == "SilentException":
            pass
        else:
            super(BaseHandler, self).log_exception(*args, **kwargs)

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        host = self.get_host_name()
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.finish(
                "<html><title>%(code)d: %(message)s</title>"
                "<body>%(code)d: %(message)s</body></html>"
                % {
                    "code": status_code,
                    "message": f"{self._reason} - {config.get_host_specific_key('errors.custom_website_error_message', host, '')}",
                }
            )

    def data_received(self, chunk):
        """Receives the data."""

    def initialize(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.tracer = None
        self.responses = []
        self.ctx = None
        super(BaseHandler, self).initialize()

    async def prepare(self) -> None:
        host = self.get_host_name()
        if not config.is_host_configured(host):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid host specified. Redirecting to main page",
            }
            log.debug(log_data)
            self.set_status(403)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid host specified",
                }
            )
            await self.finish()
            raise SilentException(log_data["message"])
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        self.tracer = None

        await self.configure_tracing()

        if config.get_host_specific_key("tornado.xsrf", host, True):
            cookie_kwargs = config.get_host_specific_key(
                "tornado.xsrf_cookie_kwargs", host, {}
            )
            self.set_cookie(
                config.get_host_specific_key("xsrf_cookie_name", host, "_xsrf"),
                self.xsrf_token,
                **cookie_kwargs,
            )
        self.request_uuid = str(uuid.uuid4())
        stats.timer("base_handler.incoming_request")
        return await self.authorization_flow()

    def write(self, chunk: Union[str, bytes, dict]) -> None:
        # host = self.get_host_name()
        # if config.get_host_specific_key(
        #     "_security_risk_full_debugging.enabled", host
        # ):
        #     if not hasattr(self, "responses"):
        #         self.responses = []
        #     self.responses.append(chunk)
        super(BaseHandler, self).write(chunk)

    async def configure_tracing(self):
        host = self.get_host_name()
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
            primary_span_name, host, tags=tracer_tags
        )
        if tracer:
            for k, v in tracer.headers.items():
                self.set_header(k, v)

    def on_finish(self) -> None:
        # host = self.get_host_name()
        if hasattr(self, "tracer") and self.tracer:
            asyncio.ensure_future(
                self.tracer.set_additional_tags({"http.status_code": self.get_status()})
            )
            asyncio.ensure_future(self.tracer.finish_spans())
            asyncio.ensure_future(self.tracer.disable_tracing())

        # if config.get_host_specific_key(
        #     "_security_risk_full_debugging.enabled", host
        # ):
        #     responses = None
        #     if hasattr(self, "responses"):
        #         responses = self.responses
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
        #         "response": responses,
        #     }
        #     with open(
        #         config.get_host_specific_key(
        #             "_security_risk_full_debugging.file", host
        #         ),
        #         "a+",
        #     ) as f:
        #         f.write(json.dumps(request_details, reject_bytes=False))
        super(BaseHandler, self).on_finish()

    async def attempt_sso_authn(self, host) -> bool:
        """
        ConsoleMe's configuration allows authenticating users by user/password, SSO, or both.
        This function helps determine how ConsoleMe should authenticate a user. If user/password login is allowed,
        users will be redirected to ConsoleMe's login page (/login). If SSO is also allowed, the Login page will present
        a button allowing the user to sign in with SSO.

        If user/password login is enabled, we don't want to give users the extra step of having to visit the login page,
        so we just authenticate them through SSO directly.
         allow authenticating users by a combination of user/password and SSO. In this case, we need to tell
        Returns: boolean
        """
        if not config.get_host_specific_key("auth.get_user_by_password", host, False):
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
        self, user: str = None, console_only: bool = True, refresh_cache: bool = False
    ) -> None:
        """Perform high level authorization flow."""
        # TODO: Prevent any sites being created with a subdomain that is a yaml keyword, ie: false, no, yes, true, etc
        # TODO: Return Authentication prompt regardless of subdomain
        self.eligible_roles = []
        self.eligible_accounts = []
        self.request_uuid = str(uuid.uuid4())
        host = self.get_host_name()
        group_mapping = get_plugin_by_name(
            config.get_host_specific_key(
                "plugins.group_mapping",
                host,
                "cmsaas_group_mapping",
            )
        )()
        auth = get_plugin_by_name(
            config.get_host_specific_key("plugins.auth", host, "cmsaas_auth")
        )()
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        refresh_cache = (
            self.request.arguments.get("refresh_cache", [False])[0] or refresh_cache
        )
        attempt_sso_authn = await self.attempt_sso_authn(host)

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
            "host": host,
        }

        log.debug(log_data)

        # Check to see if user has a valid auth cookie
        auth_cookie = self.get_cookie(
            config.get("_global_.auth.cookie.name", "consoleme_auth")
        )

        # Validate auth cookie and use it to retrieve group information
        if auth_cookie:
            res = await validate_and_return_jwt_token(auth_cookie, host)
            if res and isinstance(res, dict):
                self.user = res.get("user")
                self.groups = res.get("groups")
                self.auth_cookie_expiration = res.get("exp")

        # if host in ["localhost", "127.0.0.1"] and not self.user:
        # Check for development mode and a configuration override that specify the user and their groups.
        if config.get_host_specific_key(
            "development", host
        ) and config.get_host_specific_key("_development_user_override", host):
            self.user = config.get_host_specific_key("_development_user_override", host)
        if config.get_host_specific_key(
            "development", host
        ) and config.get_host_specific_key("_development_groups_override", host):
            self.groups = config.get_host_specific_key(
                "_development_groups_override", host
            )

        if not self.user:
            # Authenticate user by API Key
            if config.get_host_specific_key("auth.get_user_by_api_key", host, False):
                api_key = self.request.headers.get("X-API-Key")
                api_user = self.request.headers.get("X-API-User")
                if bool(api_key) != bool(api_user):
                    raise Exception(
                        "X-API-Key and X-API-User must be both present or both absent"
                    )
                if api_key and api_user:
                    ddb = UserDynamoHandler(host)
                    self.user = await ddb.verify_api_key(api_key, api_user, host)

        if not self.user:
            # SAML flow. If user has a JWT signed by ConsoleMe, and SAML is enabled in configuration, user will go
            # through this flow.

            if (
                config.get_host_specific_key("auth.get_user_by_saml", host, False)
                and attempt_sso_authn
            ):
                res = await authenticate_user_by_saml(self)
                if not res:
                    if (
                        self.request.uri != "/saml/acs"
                        and not self.request.uri.startswith("/auth?")
                    ):
                        raise SilentException(
                            "Unable to authenticate the user by SAML. "
                            "Redirecting to authentication endpoint"
                        )
                    return

        if not self.user:
            if (
                config.get_host_specific_key("auth.get_user_by_oidc", host, False)
                and attempt_sso_authn
            ):
                res = await authenticate_user_by_oidc(self)
                if not res:
                    raise SilentException(
                        "Unable to authenticate the user by OIDC. "
                        "Redirecting to authentication endpoint"
                    )
                if res and isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            if config.get_host_specific_key(
                "auth.get_user_by_aws_alb_auth", host, False
            ):
                res = await authenticate_user_by_alb_auth(self)
                if not res:
                    raise Exception("Unable to authenticate the user by ALB Auth")
                if res and isinstance(res, dict):
                    self.user = res.get("user")
                    self.groups = res.get("groups")

        if not self.user:
            # Username/Password authn flow
            if config.get_host_specific_key("auth.get_user_by_password", host, False):
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
                raise SilentException(
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
                    },
                )
                log_data["message"] = "No user detected. Check configuration."
                log.error(log_data)
                await self.finish(log_data["message"])
                raise

        self.contractor = False  # TODO: Add functionality later for contractor detection via regex or something else

        if (
            config.get_host_specific_key("auth.cache_user_info_server_side", host, True)
            and not refresh_cache
        ):
            try:
                red = await RedisHandler().redis(host)
                cache_r = red.get(f"{host}_USER-{self.user}-CONSOLE-{console_only}")
            except (redis.exceptions.ConnectionError, ClusterDownError):
                cache_r = None
            if cache_r:
                log_data["message"] = "Loading from cache"
                log.debug(log_data)
                cache = json.loads(cache_r)
                self.groups = cache.get("groups")
                self.eligible_roles = cache.get("eligible_roles")
                self.eligible_accounts = cache.get("eligible_accounts")
                self.user_role_name = cache.get("user_role_name")
                refreshed_user_roles_from_cache = True

        try:
            if not self.groups:
                try:
                    self.groups = await auth.get_groups(
                        self.user, self, headers=self.request.headers
                    )
                except Exception:
                    sentry_sdk.capture_exception()
            if not self.groups:
                raise NoGroupsException(
                    f"Groups not detected. Headers: {self.request.headers}"
                )

        except NoGroupsException:
            stats.count("Basehandler.authorization_flow.no_groups_detected")
            log_data["message"] = "No groups detected. Check configuration."
            log.error(log_data)

        # Set Per-User Role Name (This logic is not used in OSS deployment)
        if (
            config.get_host_specific_key("user_roles.opt_in_group", host)
            and config.get_host_specific_key("user_roles.opt_in_group", host)
            in self.groups
        ):
            # Get or create user_role_name attribute
            self.user_role_name = await auth.get_or_create_user_role_name(self.user)

        if not self.eligible_roles:
            self.eligible_roles = await group_mapping.get_eligible_roles(
                self.user,
                self.groups,
                self.user_role_name,
                self.get_host_name(),
                console_only=console_only,
            )

            if not self.eligible_roles:
                log_data[
                    "message"
                ] = "No eligible roles detected for user. But letting them continue"
                log.warning(log_data)
            log_data["eligible_roles"] = len(self.eligible_roles)

        if not self.eligible_accounts:
            try:
                self.eligible_accounts = await group_mapping.get_eligible_accounts(self)
                log_data["eligible_accounts"] = len(self.eligible_accounts)
                log_data["message"] = "Successfully authorized user."
                log.debug(log_data)
            except Exception:
                stats.count("Basehandler.authorization_flow.exception")
                log.error(log_data, exc_info=True)
                raise
        if (
            config.get_host_specific_key("auth.cache_user_info_server_side", host, True)
            and self.groups
            # Only set role cache if we didn't retrieve user's existing roles from cache
            and not refreshed_user_roles_from_cache
        ):
            try:
                red = await RedisHandler().redis(host)
                red.setex(
                    f"{host}_USER-{self.user}-CONSOLE-{console_only}",
                    config.get_host_specific_key(
                        "role_cache.cache_expiration", host, 60
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
            except (redis.exceptions.ConnectionError, ClusterDownError):
                pass
        if not self.get_cookie(
            config.get("_global_.auth.cookie.name", "consoleme_auth")
        ):
            expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
                minutes=config.get_host_specific_key(
                    "jwt.expiration_minutes", host, 1440
                )
            )

            encoded_cookie = await generate_jwt_token(
                self.user, self.groups, host, exp=expiration
            )
            self.set_cookie(
                config.get("_global_.auth.cookie.name", "consoleme_auth"),
                encoded_cookie,
                expires=expiration,
                secure=config.get_host_specific_key(
                    "auth.cookie.secure",
                    host,
                    "https://" in config.get_host_specific_key("url", host),
                ),
                httponly=config.get_host_specific_key(
                    "auth.cookie.httponly", host, True
                ),
                samesite=config.get_host_specific_key(
                    "auth.cookie.samesite", host, True
                ),
            )
        if self.tracer:
            await self.tracer.set_additional_tags({"USER": self.user})

        self.ctx = RequestContext(
            host=host,
            user=self.user,
            groups=self.groups,
            request_uuid=self.request_uuid,
            uri=self.request.uri,
        )


class BaseAPIV1Handler(BaseHandler):
    """Default API Handler for api/v1/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")


class BaseAPIV2Handler(BaseHandler):
    """Default API Handler for api/v2/* routes."""

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header("Content-Type", "text/plain")
            self.set_status(status_code)
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.set_header("Content-Type", "application/problem+json")
            title = httputil.responses.get(status_code, "Unknown")
            message = kwargs.get("message", self._reason)
            # self.set_status() modifies self._reason, so this call should come after we grab the reason
            self.set_status(status_code)
            self.finish(
                json.dumps(
                    {"status": status_code, "title": title, "message": message}
                )  # noqa
            )


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
        host = self.get_host_name()
        self.ctx = RequestContext(
            host=host,
            request_uuid=self.request_uuid,
            uri=self.request.uri,
        )
        if not config.is_host_configured(host):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid host specified. Redirecting to main page",
            }
            log.debug(log_data)
            self.set_status(403)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid host specified",
                }
            )
            await self.finish()
            raise SilentException(log_data["message"])
        stats = get_plugin_by_name(
            config.get("_global_.plugins.metrics", "cmsaas_metrics")
        )()
        stats.timer("base_handler.incoming_request")
        auth = get_plugin_by_name(
            config.get_host_specific_key("plugins.auth", host, "cmsaas_auth")
        )()
        if config.get_host_specific_key("auth.require_mtls", host, False):
            try:
                await auth.validate_certificate(self)
            except InvalidCertificateException:
                stats.count(
                    "GetCredentialsHandler.post.invalid_certificate_header_value"
                )
                self.set_status(403)
                self.write({"code": "403", "message": "Invalid Certificate"})
                await self.finish()
                return

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
                await self.finish()
                return
        elif config.get_host_specific_key("auth.require_jwt", host, True):
            auth_cookie = self.get_cookie(
                config.get("_global_.auth.cookie.name", "consoleme_auth")
            )

            if auth_cookie:
                res = await validate_and_return_jwt_token(auth_cookie, host)
                if not res:
                    error = {
                        "code": "invalid_jwt",
                        "message": "JWT is invalid or has expired.",
                        "request_id": self.request_uuid,
                    }
                    self.set_status(403)
                    self.write(error)
                    await self.finish()
                self.user = res.get("user")
                self.groups = res.get("groups")
                self.requester = {"type": "user", "email": self.user}
                self.current_cert_age = int(time.time()) - res.get("iat")
                self.auth_cookie_expiration = res.get("exp")
                self.ctx = RequestContext(
                    host=host,
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
        # host = self.get_host_name()
        # if config.get_host_specific_key(
        #     "_security_risk_full_debugging.enabled", host
        # ):
        #     self.responses.append(chunk)
        super(BaseMtlsHandler, self).write(chunk)

    def on_finish(self) -> None:
        # host = self.get_host_name()
        # if config.get_host_specific_key(
        #     "_security_risk_full_debugging.enabled", host
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
        #         config.get_host_specific_key(
        #             "_security_risk_full_debugging.file", host
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
