import json
import sys
import time

from tornado.web import Finish

from common.config import config
from common.exceptions.exceptions import SilentException
from common.handlers.base import BaseHandler, JwtAuthType
from common.lib.jwt import generate_jwt_token_from_cognito, validate_and_authenticate_jwt_token, validate_and_return_jwt_token
from common.lib.plugins import get_plugin_by_name

log = config.get_logger()


class AuthHandler(BaseHandler):
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
            log.debug(log_data)
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

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.set_header("Access-Control-Allow-Headers", "access-control-allow-origin,authorization,content-type") 

    async def prepare(self, *args, **kwargs):
        log.info("CognitoAuthHandler bypassing AuthHandler prepare to avoid regular auth flow")

    async def post(self, *args, **kwargs):
        log.info("CognitoAuthHandler attemps to authenticate via Cognito JWT")
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
            log.exception(exc)
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
        await self.authorization_flow(jwt_tokens=jwt_tokens, jwt_auth_type=JwtAuthType.COGNITO)

        if auth_cookie := self.get_cookie(self.get_noq_auth_cookie_key()):
            res = await validate_and_return_jwt_token(auth_cookie, self.get_tenant_name())

            # Set groups
            await self.set_groups()
            self.groups = list(set(self.groups + res.get("groups_pending_eula", [])))

            # Set roles
            await self.set_eligible_roles(False)
            self.eligible_roles = list(
                set(self.eligible_roles + res.get("additional_roles_pending_eula", []))
            )
        else:
            await self.set_groups()
            await self.set_eligible_roles(False)
            res = None

        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
                "auth_cookie": res,
            }
        )


    async def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()
