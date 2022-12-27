import tornado.escape
import tornado.web

from common.config.tenant_config import TenantConfig
from common.handlers.base import TornadoRequestHandler
from common.lib.jwt import generate_jwt_token
from common.models import UserLoginRequest, WebResponse
from common.users.models import User


class LoginHandler(TornadoRequestHandler):
    async def post(self):
        # TODO: If user email is not verified, fail login
        tenant = self.get_tenant_name()
        tenant_config = TenantConfig(tenant)
        tenant_url = self.get_tenant_url()
        # Get the username and password from the request body
        request = UserLoginRequest(**tornado.escape.json_decode(self.request.body))
        username = request.email
        mfa_token = request.mfa_token
        db_user = await User.get_by_username(tenant, username)
        if not db_user:
            db_user = await User.get_by_email(tenant, username)

        if not db_user or not await db_user.check_password(request.password):
            self.set_status(401)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid username or password"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        if db_user.mfa_enabled and not request.mfa_token:
            self.set_status(401)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "MFA Token required"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        if not db_user.email_verified:
            self.set_status(401)
            await db_user.send_verification_email(tenant_url)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={
                        "message": (
                            "Email is not verified. An email verification link was sent to you. "
                            "Please verify your email within 15 minutes of receiving the e-mail "
                            "and try again."
                        )
                    },
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        # TODO: Fix force-MFA flow
        if db_user.mfa_enabled:
            if not await db_user.check_mfa(mfa_token):
                self.set_status(401)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=403,
                        data={"message": "Invalid MFA Token. Please try again."},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

        if not db_user.mfa_enabled and request.mfa_token:
            self.set_status(401)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "MFA Token invalid"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        groups = [membership.group.name for membership in db_user.groups]
        # TODO: Get EULA Signed status
        encoded_cookie = await generate_jwt_token(
            request.email, groups, tenant, mfa_setup=db_user.mfa_enabled
        )
        # TODO: Valid auth, Mint a JWT

        self.set_cookie(
            tenant_config.auth_cookie_name,
            encoded_cookie,
            expires=tenant_config.auth_jwt_expiration_datetime,
            secure=tenant_config.auth_use_secure_cookies,
            httponly=tenant_config.auth_cookie_httponly,
            samesite=tenant_config.auth_cookie_samesite,
        )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Login successful", "user": db_user.email},
            ).dict(exclude_unset=True, exclude_none=True)
        )
