import asyncio
import sys
from datetime import datetime, timedelta

import pytz
import sentry_sdk
from email_validator import validate_email

from common.config import config
from common.handlers.base import BaseAPIV2Handler, TornadoRequestHandler
from common.lib.auth import can_admin_all

# from common.lib.cognito.auth import get_secret_hash
from common.lib.dynamo import UserDynamoHandler
from common.lib.jwt import generate_jwt_token
from common.lib.password import check_password_strength
from common.lib.web import handle_generic_error_response
from common.models import (
    AuthenticationResponse,
    LoginAttemptModel,
    RegistrationAttemptModel,
    UserManagementModel,
    WebResponse,
)

log = config.get_logger()


class UserRegistrationHandler(TornadoRequestHandler):
    """
    Allows user registration if it is configured.
    """

    async def post(self):
        # TODO: Send verification e-mail to proposed user
        tenant = self.get_tenant_name()
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to register user",
            "user-agent": self.request.headers.get("User-Agent"),
            "tenant": tenant,
        }

        generic_error_message: str = "User registration failed"
        # Fail if getting users by password is not enabled
        if not config.get_tenant_specific_key("auth.get_user_by_password", tenant):
            errors = [
                "Expected configuration `auth.get_user_by_password`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return
        # Fail if user registration not allowed
        if not config.get_tenant_specific_key("auth.allow_user_registration", tenant):
            errors = [
                "Expected configuration `auth.allow_user_registration`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return

        registration_attempt = RegistrationAttemptModel.parse_raw(self.request.body)
        log_data["username"] = registration_attempt.username
        # Fail if username not valid email address
        try:
            if not validate_email(registration_attempt.username):
                errors = ["Username must be a valid e-mail address."]
                await handle_generic_error_response(
                    self,
                    generic_error_message,
                    errors,
                    403,
                    "invalid_request",
                    log_data,
                )
                return
        except Exception as e:
            sentry_sdk.capture_exception()
            await handle_generic_error_response(
                self, generic_error_message, [str(e)], 403, "invalid_request", log_data
            )
            return
        ddb = UserDynamoHandler(tenant=tenant)
        # Fail if user already exists
        if await ddb.get_user(registration_attempt.username, tenant):
            errors = ["User already exists"]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return

        # Fails if password is not strong enough.
        password_strength_errors = await check_password_strength(
            registration_attempt.password, tenant
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
            return

        ddb.create_user(
            registration_attempt.username,
            tenant,
            registration_attempt.password,
        )

        res = WebResponse(
            status="success",
            status_code=200,
            message=f"Successfully created user {registration_attempt.username}.",
        )
        self.write(res.json(exclude_unset=True))


class LoginConfigurationHandler(TornadoRequestHandler):
    def get(self):
        tenant = self.get_tenant_name()
        default_configuration = {
            "enabled": config.get_tenant_specific_key(
                "auth.get_user_by_password", tenant
            ),
            "page_title": config.get_tenant_specific_key(
                "LoginConfigurationHandler.page_title",
                tenant,
                "Welcome to Noq - Please Sign-In",
            ),
            "allow_password_login": config.get_tenant_specific_key(
                "auth.get_user_by_password", tenant, True
            ),
            "allow_sso_login": config.get_tenant_specific_key(
                "auth.LoginConfigurationHandler.allow_sso_login",
                tenant,
                True,
            ),
            "allow_sign_up": config.get_tenant_specific_key(
                "auth.allow_user_registration", tenant, False
            ),
            "custom_message": "",
        }
        login_configuration = config.get_tenant_specific_key(
            "LoginConfigurationHandler.login_configuration",
            tenant,
            default_configuration,
        )
        self.write(login_configuration)


class LoginHandler(TornadoRequestHandler):
    """
    Handles user log-in flow if password authentication is enabled.
    """

    def check_xsrf_cookie(self):
        pass

    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json")

    async def post(self):
        tenant = self.get_tenant_name()
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to authenticate User",
            "user-agent": self.request.headers.get("User-Agent"),
            "tenant": tenant,
        }
        generic_error_message = "Authentication failed"
        if not config.get_tenant_specific_key("auth.get_user_by_password", tenant):
            errors = [
                "Expected configuration `auth.get_user_by_password`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return
        # Auth cookie must be set to use password authentication.
        if not config.get("_global_.auth.set_auth_cookie", True):
            errors = [
                "Expected configuration `_global_.auth.set_auth_cookie`, but it is not enabled."
            ]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "not_configured", log_data
            )
            return

        login_attempt = LoginAttemptModel.parse_raw(self.request.body)
        log_data["username"] = login_attempt.username
        log_data["after_redirect_uri"] = login_attempt.after_redirect_uri
        if not login_attempt.username:
            errors = ["Username is required"]
            await handle_generic_error_response(
                self, generic_error_message, errors, 400, "username_required", log_data
            )
            return
        if not login_attempt.password:
            errors = ["Password is required"]
            await handle_generic_error_response(
                self, generic_error_message, errors, 400, "password_required", log_data
            )
            return
        # if config.get_tenant_specific_key(
        #     "auth.get_user_by_cognito_user_pool", tenant
        # ):
        #     user = await get_user_by_cognito_user_pool(
        #         self, login_attempt.username, login_attempt.password
        #     )
        #     secret_hash = get_secret_hash(username)
        ddb = UserDynamoHandler(tenant=tenant)
        authenticated_response: AuthenticationResponse = await ddb.authenticate_user(
            login_attempt, tenant
        )
        if not authenticated_response.authenticated:
            # Wait 1 second to protect from single-tenant brute-force
            await asyncio.sleep(1)
            await handle_generic_error_response(
                self,
                generic_error_message,
                authenticated_response.errors,
                403,
                "authentication_failure",
                log_data,
            )
            return
        # Make and set jwt for user
        expiration = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(
            minutes=config.get_tenant_specific_key(
                "jwt.expiration_minutes", tenant, 1200
            )
        )
        encoded_cookie = await generate_jwt_token(
            authenticated_response.username,
            authenticated_response.groups,
            tenant,
            exp=expiration,
        )
        self.set_cookie(
            config.get("_global_.auth.cookie.name", "noq_auth"),
            encoded_cookie,
            expires=expiration,
            secure=config.get_tenant_specific_key(
                "auth.cookie.secure",
                tenant,
                True
                if "https://" in config.get_tenant_specific_key("url", tenant)
                else False,
            ),
            httponly=config.get_tenant_specific_key(
                "auth.cookie.httponly", tenant, True
            ),
            samesite=config.get_tenant_specific_key(
                "auth.cookie.samesite", tenant, True
            ),
        )
        res = WebResponse(
            status="redirect",
            redirect_url=login_attempt.after_redirect_uri,
            status_code=200,
            reason="authenticated_redirect",
            message="User has successfully authenticated. Redirecting to their intended destination.",
        )
        self.write(res.json(exclude_unset=True, exclude_none=True))


class UserManagementHandler(BaseAPIV2Handler):
    """
    Handles creating and updating users. Only authorized users are allowed to access this endpoint.
    """

    async def post(self):
        tenant = self.ctx.tenant
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "message": "Create/Update User",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "ip": self.ip,
            "tenant": tenant,
        }

        generic_error_message = "Unable to create/update user"
        log.debug(log_data)
        # Checks authz levels of current user
        if not can_admin_all(self.user, self.groups, tenant):
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return
        ddb = UserDynamoHandler(tenant=tenant)
        request = UserManagementModel.parse_raw(self.request.body)
        log_data["requested_user"] = request.username
        if request.user_management_action.value == "create":
            log.debug(
                {
                    **log_data,
                    "message": "Creating user",
                    "requested_user": request.username,
                    "requested_groups": request.groups,
                }
            )

            # Fails if password is not strong enough.
            password_strength_errors = await check_password_strength(
                request.password, tenant
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
                return

            ddb.create_user(
                request.username,
                tenant,
                request.password,
                request.groups,
            )
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully created user {request.username}.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        elif request.user_management_action.value == "update":
            log.debug(
                {
                    **log_data,
                    "message": "Updating user",
                    "requested_user": request.username,
                    "requested_groups": request.groups,
                }
            )

            if request.password:
                # Fails if password is not strong enough.
                password_strength_errors = await check_password_strength(
                    request.password, tenant
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
                    return
            ddb.update_user(
                request.username,
                tenant,
                password=request.password,
                groups=request.groups,
            )
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully updated user {request.username}.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        elif request.user_management_action.value == "delete":
            log.debug(
                {
                    **log_data,
                    "message": "Deleting user",
                    "requested_user": request.username,
                }
            )
            ddb.delete_user(
                request.username,
                tenant,
            )
            res = WebResponse(
                status="success",
                status_code=200,
                message=f"Successfully deleted user {request.username}.",
            )
            self.write(res.json(exclude_unset=True, exclude_none=True))
            return
        else:
            errors = ["Change type is not supported by this endpoint."]
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "invalid_request", log_data
            )
            return
