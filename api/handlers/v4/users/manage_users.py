import base64
import sys
import urllib.parse

import tornado.escape
import tornado.gen
import tornado.web
from email_validator import validate_email

from common.config.tenant_config import TenantConfig
from common.handlers.base import BaseAdminHandler, BaseHandler, TornadoRequestHandler
from common.lib.filter import PaginatedQueryResponse, filter_data_with_sqlalchemy
from common.lib.jwt import generate_jwt_token
from common.lib.password import check_password_strength, generate_random_password
from common.lib.tenant.models import TenantDetails
from common.lib.web import handle_generic_error_response
from common.models import WebResponse
from common.users.models import User


class ManageListUsersHandler(BaseAdminHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        tenant = self.ctx.db_tenant

        _filter = data.get("filter", {})

        try:
            query_response: PaginatedQueryResponse = await filter_data_with_sqlalchemy(
                _filter, tenant, User
            )
        except Exception as exc:
            errors = [str(exc)]
            self.write(
                WebResponse(
                    errors=errors,
                    status_code=500,
                    count=len(errors),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            self.set_status(500, reason=str(exc))
            raise tornado.web.Finish()

        res = [x.dict() for x in query_response.data]
        query_response.data = res

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=query_response.dict(exclude_unset=True, exclude_none=True),
            ).dict(exclude_unset=True, exclude_none=True)
        )


# Define the handler for the create user route
class ManageUsersHandler(BaseAdminHandler):
    async def get(self):
        users = User()
        all_users = await users.get_all(self.ctx.db_tenant, get_groups=True)
        users = []
        for user in all_users:
            users.append(
                {
                    "id": str(user.id),
                    "email": user.email,
                    "groups": [group.name for group in user.groups],
                }
            )
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"users": users},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Creating new user",
        }

        tenant_url = self.get_tenant_url()

        # Get the username and password from the request body
        data = tornado.escape.json_decode(self.request.body)
        email = data.get("email")
        username = (
            email  # We need to support separate username/email when we support SCIM
        )
        password_supplied = True
        password = data.get("password")
        if not password:
            password_supplied = False
            password = await generate_random_password()

        if not validate_email(email):
            self.set_status(403)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid e-mail address"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        # Check if a user with the same username already exists
        existing_user = await User.get_by_email(self.ctx.db_tenant, username)
        if existing_user:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Username or email already taken"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        # TODO: Check password strength
        password_strength_errors = await check_password_strength(
            password, self.ctx.tenant
        )
        if password_strength_errors:
            await handle_generic_error_response(
                self,
                password_strength_errors["message"],
                password_strength_errors["errors"],
                403,
                "weak_password",
                log_data,
            )
            raise tornado.web.Finish()

        created_user = await User.create(
            self.ctx.db_tenant, username, email, password, managed_by="MANUAL"
        )

        if not password_supplied:
            await created_user.send_password_via_email(tenant_url, password)

        # Return a JSON object with the user's ID
        self.write({"user_id": created_user.id, "username": created_user.username})

    async def put(self):
        # Get the user id and security action from the request
        user_id = self.get_argument("user_id")
        action = self.get_argument("action")
        data = tornado.escape.json_decode(self.request.body or "{}")

        # Update the user's security in the database
        user = await User.get_by_id(self.ctx.db_tenant, user_id)

        if not user:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid user"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        if action == "reset_password":
            # Generate a new random password for the user
            new_password = await generate_random_password()
            user.set_password(new_password)
            self.write({"success": True, "new_password": new_password})
        elif action == "reset_mfa":
            user.mfa_secret = None
            self.write({"success": True})
        elif action == "update_user":
            if data.get("active"):
                user.active = data.get("active")
            if data.get("username"):
                user.username = data.get("username")
            if data.get("email"):
                user.email = data.get("email")
            if data.get("display_name"):
                user.display_name = data.get("display_name")
            if data.get("full_name"):
                user.full_name = data.get("full_name")
            if data.get("given_name"):
                user.given_name = data.get("given_name")
            if data.get("middle_name"):
                user.middle_name = data.get("middle_name")
            if data.get("family_name"):
                user.family_name = data.get("family_name")
        else:
            self.set_status(400)
            self.write({"error": "Invalid action"})
        new_user = await user.update(
            user, id=user.id, username=user.username, email=user.email
        )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=new_user.dict(),
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        email = data.get("email")

        user = await User.get_by_email(self.ctx.db_tenant, email)
        if not user:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid user"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        res = await user.delete()
        if not res:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Unable to delete user"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Successfully deleted user"},
            ).dict(exclude_unset=True, exclude_none=True)
        )


class PasswordResetSelfServiceHandler(BaseHandler):
    async def post(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Resetting User Password",
        }

        data = tornado.escape.json_decode(self.request.body)
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        tenant = self.get_tenant_name()
        tenant_config = TenantConfig(tenant)
        db_user = await User.get_by_username(self.ctx.db_tenant, self.user)
        if not db_user:
            db_user = await User.get_by_email(self.ctx.db_tenant, self.user)

        if not db_user:
            await handle_generic_error_response(
                self,
                "User not found",
                [],
                403,
                "user_not_found",
                log_data,
            )
            raise tornado.web.Finish()

        if not current_password or not new_password:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Current password is required"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        if not db_user or not await db_user.check_password(current_password):
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid password"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        password_strength_errors = await check_password_strength(
            new_password, self.ctx.tenant
        )
        if password_strength_errors:
            await handle_generic_error_response(
                self,
                password_strength_errors["message"],
                password_strength_errors["errors"],
                403,
                "weak_password",
                log_data,
            )
            raise tornado.web.Finish()

        await db_user.user_initiated_password_reset(new_password)
        # Refresh DB User and set cookie
        db_user = await User.get_by_username(
            self.ctx.db_tenant, self.user, get_groups=True
        )
        if not db_user:
            db_user = await User.get_by_email(self.ctx.db_tenant, get_groups=True)
        groups = [group.name for group in db_user.groups]
        tenant_details = await TenantDetails.get(tenant)
        eula_signed = bool(tenant_details.eula_info)
        mfa_setup_required = not db_user.mfa_enabled
        encoded_cookie = await generate_jwt_token(
            self.user,
            self.groups,
            tenant,
            mfa_setup_required=mfa_setup_required,
            mfa_verification_required=self.mfa_verification_required,
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
                    "message": "Password successfully changed",
                    "user": db_user.email,
                    "groups": groups,
                    "mfa_setup_required": mfa_setup_required,
                    "eula_signed": eula_signed,
                    "password_reset_required": db_user.password_reset_required,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )


class UnauthenticatedPasswordResetSelfServiceHandler(TornadoRequestHandler):
    async def get(self):
        # The user clicked the link in the email, so we need to show them the reset form
        # extract the email and verification code from the request
        token = self.get_argument("token")

        try:
            password_reset_blob_j = base64.b64decode(token).decode("utf-8")
        except Exception:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        try:
            password_reset_blob = tornado.escape.json_decode(password_reset_blob_j)
        except Exception:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        email = password_reset_blob.get("email")
        if not email or not validate_email(email):
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        tenant = password_reset_blob.get("tenant")
        if not tenant:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        user = await User.get_by_email(self.ctx.db_tenant, email)

        if not user:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        password_reset_token = password_reset_blob.get("password_reset_token")
        if not password_reset_token:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        verified = await user.verify_password_reset_token(password_reset_token)
        if not verified:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Password reset token is valid."},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def post(self):
        # The user requested the reset, so we need to email them
        log_data = {}
        success_message = (
            "If your user exists, we have sent you an email with a password reset link "
            "that is valid for 15 minutes. "
            "Please check your email to reset your password."
        )
        success_response = WebResponse(
            success="success",
            status_code=200,
            data={"message": success_message},
        ).dict(exclude_unset=True, exclude_none=True)

        data = tornado.escape.json_decode(self.request.body)
        command = data.get("command")
        tenant = self.get_tenant_name()
        tenant_url = self.get_tenant_url()

        if command == "request":
            # Send the reset email
            email = data.get("email")
            user = await User.get_by_email(self.ctx.db_tenant, email)
            if not user:
                self.set_status(200)
                # We give an identical response to the user if the email is not found to prevent
                # enumeration attacks.
                self.write(success_response)
                raise tornado.web.Finish()
            await user.send_password_reset_email(tenant_url)
            self.write(success_response)
            raise tornado.web.Finish()
        elif command == "reset":
            # Reset the password
            password = data.get("password")
            token = data.get("token")

            parsed_token = urllib.parse.unquote(token)
            password_reset_blob_j = base64.urlsafe_b64decode(parsed_token).decode(
                "utf-8"
            )
            password_reset_blob = tornado.escape.json_decode(password_reset_blob_j)
            if not password_reset_blob:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid token"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            email = password_reset_blob.get("email")
            if not email or not validate_email(email):
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid email address"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            tenant = password_reset_blob.get("tenant")
            if not tenant:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid tenant"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            user = await User.get_by_email(self.ctx.db_tenant, email)

            if not user:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid user"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            password_reset_token = password_reset_blob.get("password_reset_token")
            if not password_reset_token:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid token"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            verified = await user.verify_password_reset_token(password_reset_token)
            if not verified:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid token"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()

            # Check password strength
            password_strength_errors = await check_password_strength(password, tenant)
            if password_strength_errors:
                await handle_generic_error_response(
                    self,
                    password_strength_errors["message"],
                    password_strength_errors["errors"],
                    403,
                    "weak_password",
                    log_data,
                )
                raise tornado.web.Finish()
            if not await user.reset_password(
                tenant, email, password_reset_token, password
            ):
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Unable to reset password"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data={"message": "Password reset successfully"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()


# TODO: Handle user MFA CRUD
class UserMFASelfServiceHandler(BaseHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        command = data.get("command")
        if not command:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid request"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        user = await User.get_by_email(self.ctx.db_tenant, self.user)
        if not user:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid user"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        if command == "setup":
            # Set up MFA
            await user.set_mfa_secret_temp()
            totp_uri = await user.get_totp_uri(self.ctx.tenant)
            mfa_secret = user.mfa_secret_temp
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data={
                        "message": "Please install and verify your MFA",
                        "totp_uri": totp_uri,
                        "mfa_secret": mfa_secret,
                    },
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()
        elif command == "verify":
            # Verify MFA
            mfa_token = data.get("mfa_token")
            if not mfa_token:
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Missing MFA token"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            if not await user.enable_mfa(mfa_token):
                self.set_status(403)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Invalid MFA token"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            else:
                user = await User.get_by_email(self.ctx.db_tenant, self.user)
                tenant_config = TenantConfig(self.ctx.tenant)
                encoded_cookie = await generate_jwt_token(
                    self.user,
                    self.groups,
                    self.ctx.tenant,
                    mfa_setup_required=not user.mfa_enabled,
                    mfa_verification_required=False,
                    eula_signed=self.ctx.needs_to_sign_eula,
                    password_reset_required=user.password_reset_required,
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
                            "message": "MFA verified",
                        },
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()


class UnauthenticatedEmailVerificationHandler(tornado.web.RequestHandler):
    async def get(self):
        # extract the email and verification code from the request
        token = self.get_argument("token")

        email_verify_blob_j = base64.b64decode(token).decode("utf-8")

        email_verify_blob = tornado.escape.json_decode(email_verify_blob_j)

        email = email_verify_blob.get("email")
        if not email or not validate_email(email):
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid email address"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        tenant = email_verify_blob.get("tenant")
        if not tenant:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid tenant"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        email_verify_token = email_verify_blob.get("email_verify_token")
        if not email_verify_token:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Invalid token"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        verified = await User.verify_email(tenant, email, email_verify_token)

        if not verified:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "failed to verify email"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            # TODO: Log here
            raise tornado.web.Finish()

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={
                    "message": "Successfully verified e-mail",
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )
