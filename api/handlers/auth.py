import json
import logging
import sys
import time

import sentry_sdk
from tornado.web import Finish

from common.config import config
from common.handlers.base import BaseHandler, JwtAuthType
from common.models import WebResponse

log = config.get_logger()


def log_dict_handler(
    log_level: str,
    handler_class: BaseHandler,
    account_id: str = None,
    role_name: str = None,
    tenant: str = None,
    exc: dict = {},
    **kwargs: dict,
):
    if not log_level.upper() in [
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        "exception",
    ]:
        log_level = "info"
    if not tenant:
        tenant = handler_class.get_tenant_name()
    log_data = {
        "function": f"{__name__}.{handler_class.__class__.__name__}.{sys._getframe().f_code.co_name}",
        "user-agent": handler_class.request.headers.get("User-Agent"),
        "request_id": handler_class.request_uuid,
        "account_id": account_id if account_id else "unknown",
        "role_name": role_name if role_name else "unknown",
        "tenant": tenant,
    }
    log_data.update(kwargs)  # Add any other log data
    if log_level.upper() in ["ERROR", "CRITICAL", "EXCEPTION"]:
        log_data["exception"] = exc
    getattr(log, getattr(logging, log_level.upper()))(log_data)
    sentry_sdk.capture_exception(tags={"user": handler_class.user})


class AuthHandler(BaseHandler):
    async def prepare(self):
        tenant = self.get_tenant_name()
        if not config.is_tenant_configured(tenant):
            log_dict_handler("debug", self, tenant=tenant)
            self.set_status(403)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid tenant specified",
                }
            )
            raise Finish("Invalid tenant specified.")
        try:
            if self.request.method.lower() in ["options", "post"]:
                return
            await super(AuthHandler, self).prepare()
        except:  # noqa
            # NoUserException
            raise

    async def get(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )

    async def post(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )


class CognitoAuthHandler(AuthHandler):
    def set_xsrf_cookie(self):
        pass

    async def prepare(self, *args, **kwargs):
        self.set_header(
            "Access-Control-Allow-Origin", self.request.headers.get("origin", "*")
        )
        self.set_header("Access-Control-Allow-Methods", ",".join(self.allowed_methods))
        self.set_header(
            "Access-Control-Allow-Headers",
            "x-requested-with,access-control-allow-origin,authorization,content-type",
        )
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header("Content-Type", "application/json")

    async def get(self, *args, **kwargs):
        tenant = self.get_tenant_name()
        user_pool_region = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_region", tenant, config.region
        )
        if not user_pool_region:
            raise Exception("User pool region is not defined")
        user_pool_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_id", tenant
        )
        if not user_pool_id:
            raise Exception("User pool is not defined")
        client_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_client_id", tenant
        )
        if not client_id:
            raise Exception("Client ID is not defined")

        tenant_details = {
            "client_id": client_id,
            "user_pool_id": user_pool_id,
            "user_pool_region": user_pool_region,
        }
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=tenant_details,
            ).json(exclude_unset=True, exclude_none=True)
        )

    async def post(self, *args, **kwargs):
        await self.initialize_auth()
        try:
            body = json.loads(self.request.body)
        except json.decoder.JSONDecodeError:
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid JWT token",
                }
            )
            return self.finish()
        except Exception as exc:
            log_dict_handler("exception", self, exc=exc)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid JWT token",
                }
            )
            return self.finish()
        jwt_tokens = body.get("jwtToken", {})
        await self.authorization_flow(
            jwt_tokens=jwt_tokens, jwt_auth_type=JwtAuthType.COGNITO
        )

        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )

    async def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()
