from tornado.web import Finish

import common.lib.noq_json as json
from common.config import config
from common.handlers.base import BaseHandler, JwtAuthType, TornadoRequestHandler
from common.models import WebResponse

log = config.get_logger(__name__)


class AuthHandler(BaseHandler):
    async def prepare(self):
        tenant = self.get_tenant_name()
        if not config.is_tenant_configured(tenant):
            log.debug("Invalid tenant specified", tenant=tenant)
            self.set_status(406)
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
        await super(AuthHandler, self).prepare()

    async def get(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "user": self.user,
            }
        )

    async def post(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "user": self.user,
            }
        )


class CognitoAuthHandler(BaseHandler):
    def check_xsrf_cookie(self) -> None:
        pass

    async def post(self, *args, **kwargs):
        await self.authorization_flow()
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
            log.exception("Invalid JWT token", exc=exc)
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
                "user": self.user,
            }
        )

    async def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()


class UnauthenticatedAuthSettingsHandler(TornadoRequestHandler):
    def check_xsrf_cookie(self) -> None:
        pass

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
        # if config.get_tenant_specific_key("auth.get_user_by_saml", tenant, False):
        #     pass
        # if config.get_tenant_specific_key("auth.get_user_by_oidc", tenant, False):
        #     pass
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=tenant_details,
            ).json(exclude_unset=True, exclude_none=True)
        )
