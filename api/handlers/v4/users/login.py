import tornado.escape
import tornado.web

from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseHandler, TornadoRequestHandler
from common.lib.jwt import generate_jwt_token
from common.lib.tenant.models import TenantDetails
from common.models import UserLoginRequest, UserMfaVerificationRequest, WebResponse
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
        db_user = await User.get_by_username(tenant, username, get_groups=True)
        if not db_user:
            db_user = await User.get_by_email(tenant, username, get_groups=True)

        if not db_user or not await db_user.check_password(request.password):
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid username or password"},
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

        mfa_verification_required = db_user.mfa_enabled

        if mfa_verification_required and mfa_token:
            if await db_user.check_mfa(mfa_token):
                mfa_verification_required = False
            else:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=403,
                        data={"message": "Invalid MFA Token. Please try again."},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

        if not db_user.mfa_enabled and request.mfa_token:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "MFA Token invalid"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        groups = [group.name for group in db_user.groups]
        tenant_details = await TenantDetails.get(tenant)
        eula_signed = bool(tenant_details.eula_info)
        mfa_setup_required = not db_user.mfa_enabled

        encoded_cookie = await generate_jwt_token(
            request.email,
            groups,
            tenant,
            mfa_setup_required=mfa_setup_required,
            mfa_verification_required=mfa_verification_required,
            eula_signed=eula_signed,
            password_reset_required=db_user.password_reset_required,
        )

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
                data={
                    "message": "Login successful",
                    "user": db_user.email,
                    "groups": groups,
                    "mfa_setup_required": mfa_setup_required,
                    "mfa_verification_required": mfa_verification_required,
                    "eula_signed": eula_signed,
                    "password_reset_required": db_user.password_reset_required,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )


class MfaHandler(BaseHandler):
    async def post(self):
        request = UserMfaVerificationRequest(
            **tornado.escape.json_decode(self.request.body)
        )
        db_user = await User.get_by_username(
            self.ctx.tenant, self.user, get_groups=True
        )
        if not db_user:
            db_user = await User.get_by_email(
                self.ctx.tenant, self.user, get_groups=True
            )
        if not db_user:
            self.set_status(401)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid mfa token"},
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

        if not await db_user.check_mfa(request.mfa_token):
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid mfa token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        tenant_config = TenantConfig(self.ctx.tenant)
        encoded_cookie = await generate_jwt_token(
            self.user,
            self.groups,
            self.ctx.tenant,
            mfa_setup_required=not db_user.mfa_enabled,
            mfa_verification_required=False,  # Mfa was verified
            eula_signed=self.eula_signed,
            password_reset_required=db_user.password_reset_required,
        )

        self.set_cookie(
            tenant_config.auth_cookie_name,
            encoded_cookie,
            expires=tenant_config.auth_jwt_expiration_datetime,
            secure=tenant_config.auth_use_secure_cookies,
            httponly=tenant_config.auth_cookie_httponly,
            samesite=tenant_config.auth_cookie_samesite,
        )
