import base64
import sys
import urllib.parse

import tornado.escape
import tornado.gen
import tornado.web
from email_validator import validate_email

from common.handlers.base import BaseAdminHandler, BaseHandler, TornadoRequestHandler
from common.lib.password import check_password_strength, generate_random_password
from common.lib.web import handle_generic_error_response
from common.models import WebResponse
from common.users.models import User


# Define the handler for the create user route
class ManageUsersHandler(BaseAdminHandler):
    async def get(self):
        users = User()
        all_users = await users.get_all(self.ctx.tenant)
        users = []
        for user in all_users:
            users.append(
                {
                    "id": str(user.id),
                    "email": user.email,
                    "groups": [membership.group.name for membership in user.groups],
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

        # Get the username and password from the request body
        data = tornado.escape.json_decode(self.request.body)
        email = data.get("email")
        username = (
            email  # We need to support separate username/email when we support SCIM
        )
        password = data.get("password")
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
        existing_user = await User.get_by_email(self.ctx.tenant, username)
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

        created_user = await User.create(self.ctx.tenant, username, email, password)

        # Return a JSON object with the user's ID
        self.write({"user_id": created_user.id, "username": created_user.username})

    async def put(self):
        # Get the user id and security action from the request
        user_id = self.get_argument("user_id")
        action = self.get_argument("action")

        # Update the user's security in the database
        try:
            user = self.db.query(User).filter(User.id == user_id).one()
            if action == "reset_password":
                # Generate a new random password for the user
                new_password = generate_random_password()
                user.set_password(new_password)
                self.write({"success": True, "new_password": new_password})
            elif action == "reset_mfa":
                user.mfa_secret = None
                self.write({"success": True})
            else:
                self.set_status(400)
                self.write({"error": "Invalid action"})
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.set_status(500)
            self.write({"error": str(e)})

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        email = data.get("email")
        user = await User.get_by_email(self.ctx.tenant, email)
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


class UnauthenticatedPasswordResetSelfServiceHandler(TornadoRequestHandler):
    async def get(self):
        # The user clicked the link in the email, so we need to show them the reset form
        # extract the email and verification code from the request
        token = self.get_argument("token")

        password_reset_blob_j = base64.b64decode(token).decode("utf-8")

        password_reset_blob = tornado.escape.json_decode(password_reset_blob_j)

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

        user = await User.get_by_email(tenant, email)

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
        data = tornado.escape.json_decode(self.request.body)
        command = data.get("command")
        email = data.get("email")
        if not email:
            self.set_status(400)
            self.write(
                self.write(
                    WebResponse(
                        success="error",
                        status_code=400,
                        data={"message": "Unable to reset password"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
            )
            raise tornado.web.Finish()
        tenant = self.get_tenant_name()
        tenant_url = self.get_tenant_url()
        user = await User.get_by_email(tenant, email)
        success_response = WebResponse(
            success="success",
            status_code=200,
            data={"message": success_message},
        ).dict(exclude_unset=True, exclude_none=True)
        if not user:
            self.set_status(200)
            # We give an identical response to the user if the email is not found to prevent
            # enumeration attacks.
            self.write(success_response)
            raise tornado.web.Finish()
        if command == "request":
            # Send the reset email
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

            user = await User.get_by_email(tenant, email)

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
        user = await User.get_by_email(self.ctx.tenant, self.user)
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
            await user.set_mfa_secret()
            totp_uri = await user.get_totp_uri()
            self.write(
                WebResponse(
                    success="success",
                    status_code=200,
                    data={
                        "message": "Please install and verify your MFA",
                        "totp_uri": totp_uri,
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
