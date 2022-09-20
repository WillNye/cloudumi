import asyncio

import boto3
import tornado.web

from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.config import config
from common.handlers.base import BaseHandler
from common.lib.cognito import identity
from common.lib.cognito.identity import CognitoUserClient
from common.lib.jwt import validate_and_return_jwt_token
from common.lib.web import handle_generic_error_response
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SetupMfaRequestModel,
    SSOIDPProviders,
)

LOG = config.get_logger()


class IdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _config_key = "IdentityProvider"
    _user_pool_id = None
    _user_pool_client_id = None
    _model_class = None
    _sso_idp_attr = None
    _user_pool_region = None

    @property
    def user_pool_id(self) -> str:
        if user_pool_id := self._user_pool_id:
            return user_pool_id

        user_pool_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.tenant
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        self._user_pool_id = user_pool_id
        return user_pool_id

    @property
    def user_pool_region(self) -> str:
        if user_pool_region := self._user_pool_region:
            return user_pool_region

        user_pool_region = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_region", self.ctx.tenant, config.region
        )
        if not user_pool_region:
            raise ValueError("Cognito user pool region not configured")

        self._user_pool_region = user_pool_region
        return user_pool_region

    @property
    def user_pool_client_id(self) -> str:
        if user_pool_client_id := self._user_pool_client_id:
            return user_pool_client_id

        user_pool_client_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_client_id", self.ctx.tenant
        )
        if not user_pool_client_id:
            raise ValueError("Cognito user pool client id not configured")

        self._user_pool_client_id = user_pool_client_id
        return user_pool_client_id

    async def _retrieve(self) -> dict:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)

        try:
            sso_idp_provider = await identity.get_identity_providers(
                self.user_pool_id, client=cognito_idp, mask_secrets=True
            )
        except cognito_idp.exceptions.ResourceNotFoundException:
            raise ValueError

        if (
            self._sso_idp_attr
        ):  # If a specific identity provider was specified only provide that one
            provider_val = getattr(sso_idp_provider, self._sso_idp_attr, None)
            return provider_val.dict() if provider_val else {}

        return sso_idp_provider.dict()

    async def _create(self, data):
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)
        if not self._sso_idp_attr:  # Upsert all the things
            sso_idp_provider = self._model_class(**data)
            sso_idp_provider.provider_name = sso_idp_provider.provider_type
        else:
            sso_idp_provider = SSOIDPProviders()
            setattr(sso_idp_provider, self._sso_idp_attr, self._model_class(**data))

        return await identity.upsert_identity_provider(
            self.user_pool_id,
            self.user_pool_client_id,
            sso_idp_provider,
            client=cognito_idp,
        )

    async def _delete(self) -> bool:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)

        try:
            sso_idp_provider = await identity.get_identity_providers(
                self.user_pool_id, client=cognito_idp
            )
        except cognito_idp.exceptions.ResourceNotFoundException:
            raise ValueError

        if (
            self._sso_idp_attr
        ):  # If a specific identity provider was specified only delete that one
            provider = getattr(sso_idp_provider, self._sso_idp_attr, None)
            await identity.disconnect_idp_from_app_client(
                self.user_pool_id,
                self.user_pool_client_id,
                provider,
                client=cognito_idp,
            )
            return await identity.delete_identity_provider(
                self.user_pool_id, provider, client=cognito_idp
            )
        else:  # Delete all supported providers
            supported_providers = list(SSOIDPProviders.__dict__["__fields__"].keys())
            deleted = True  # Have an all or nothing id on deleted so we don't exit on first bad delete
            for provider_type in supported_providers:
                # If a request is being made to set an already defined provider, remove the existing provider
                if provider := getattr(sso_idp_provider, provider_type):
                    await identity.disconnect_idp_from_app_client(
                        self.user_pool_id,
                        self.user_pool_client_id,
                        provider,
                        client=cognito_idp,
                    )
                    if not await identity.delete_identity_provider(
                        self.user_pool_id, provider, client=cognito_idp
                    ):
                        deleted = False

        return deleted


class GoogleOidcIdpConfigurationCrudHandler(IdpConfigurationCrudHandler):
    _model_class = GoogleOIDCSSOIDPProvider
    _sso_idp_attr = "google"


class SamlOidcIdpConfigurationCrudHandler(IdpConfigurationCrudHandler):
    _model_class = SamlOIDCSSOIDPProvider
    _sso_idp_attr = "saml"


class OidcIdpConfigurationCrudHandler(IdpConfigurationCrudHandler):
    _model_class = OIDCSSOIDPProvider
    _sso_idp_attr = "oidc"


class SsoIdpProviderConfigurationCrudHandler(IdpConfigurationCrudHandler):
    _model_class = SSOIDPProviders


class CognitoCrudHandler(MultiItemConfigurationCrudHandler):
    _config_key = "Unused"
    _user_pool_id = None
    _user_pool_region = None

    @property
    def user_pool_id(self) -> str:
        if user_pool_id := getattr(self, "_user_pool_id"):
            return user_pool_id

        user_pool_id = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.tenant
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        self._user_pool_id = user_pool_id
        return user_pool_id

    @property
    def user_pool_region(self) -> str:
        if user_pool_region := self._user_pool_region:
            return user_pool_region

        user_pool_region = config.get_tenant_specific_key(
            "secrets.cognito.config.user_pool_region", self.ctx.tenant, config.region
        )
        if not user_pool_region:
            raise ValueError("Cognito user pool region not configured")

        self._user_pool_region = user_pool_region
        return user_pool_region


class CognitoUserCrudHandler(CognitoCrudHandler):
    _model_class = CognitoUser
    _identifying_keys = ["Username"]

    async def _retrieve(self) -> list[dict]:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)
        users = list()
        try:
            identity_users = await identity.CognitoUserClient(
                self.user_pool_id
            ).list_users()
        except cognito_idp.exceptions.ResourceNotFoundException:
            return []

        for user in identity_users:
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword", None)
            for attr in user_dict.get("Attributes", []):
                if attr["Name"] == "email":
                    user_dict["Username"] = attr["Value"]
                    break

            users.append(user_dict)

        return users

    async def _create(self, data) -> CognitoUser:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)

        try:
            # Update the resource
            cognito_user = self._model_class(**data)
            cognito_user.Groups = await asyncio.gather(
                *[
                    identity.get_identity_group(
                        self.user_pool_id, group, client=cognito_idp
                    )
                    for group in cognito_user.Groups
                ]
            )
            await identity.upsert_identity_user_group(
                self.user_pool_id, cognito_user, client=cognito_idp
            )
        except cognito_idp.exceptions.UserNotFoundException:
            # Resource doesn't exist, so create it
            return await identity.CognitoUserClient(self.user_pool_id).create_user(
                self._model_class(**data)
            )

    async def _delete(self, data) -> bool:
        return await identity.CognitoUserClient(self.user_pool_id).delete_user(
            self._model_class(**data).Username
        )


class CognitoGroupCrudHandler(CognitoCrudHandler):
    _model_class = CognitoGroup
    _identifying_keys = ["GroupName"]

    async def _retrieve(self) -> list[dict]:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)
        try:
            return [
                group.dict()
                for group in await identity.get_identity_groups(
                    self.user_pool_id, client=cognito_idp
                )
            ]
        except cognito_idp.exceptions.ResourceNotFoundException:
            return []

    async def _create(self, data) -> CognitoGroup:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)
        try:
            # Update the resource
            cognito_group = await identity.get_identity_group(
                self.user_pool_id, data["GroupName"], client=cognito_idp
            )
            if (
                description := data.get("Description")
            ) and description != cognito_group.Description:
                cognito_group.Description = description
                return await identity.update_identity_group(
                    self.user_pool_id, cognito_group, client=cognito_idp
                )

        except cognito_idp.exceptions.ResourceNotFoundException:
            # Resource doesn't exist, so create it
            return await identity.create_identity_group(
                self.user_pool_id, self._model_class(**data), client=cognito_idp
            )

    async def _delete(self, data) -> bool:
        cognito_idp = boto3.client("cognito-idp", region_name=self.user_pool_region)
        return await identity.delete_identity_group(
            self.user_pool_id, self._model_class(**data), client=cognito_idp
        )


class CognitoUserResetMFA(BaseHandler):
    async def post(self, username: str = None):
        if username and not self.is_admin:
            errors = ["User is not authorized to access this endpoint."]
            await handle_generic_error_response(
                self, errors[0], errors, 403, "unauthorized", {}
            )
            raise tornado.web.Finish()

        username = username or self.user
        cognito_user_client = CognitoUserClient.tenant_client(self.ctx.tenant)
        cognito_user_client.update_user_mfa_status(username, False)

        response_json = {
            "status": "success",
            "message": "Successfully reset user MFA",
            "username": username,
        }
        self.write(response_json)


class CognitoUserSetupMFA(BaseHandler):
    async def get(self):
        self.write(self.mfa_setup)

    async def post(self):
        tenant = self.ctx.tenant
        user_client = CognitoUserClient.tenant_client(tenant)
        mfa_request = SetupMfaRequestModel.parse_raw(self.request.body)

        try:
            user_client.verify_mfa(
                mfa_request.user_code,
                access_token=mfa_request.access_token,
                email=self.user,
            )
            self.mfa_setup = None

            # Issue a new JWT with proper groups
            if auth_cookie := self.get_cookie(self.get_noq_auth_cookie_key()):
                await validate_and_return_jwt_token(auth_cookie, tenant)
                await self.set_jwt_cookie(tenant)

            self.write(
                {
                    "status": "success",
                    "message": "Successfully setup user MFA",
                    "status_code": 200,
                }
            )
        except Exception as err:
            message = "Unable to complete the MFA setup."
            log_data = {
                "user": self.user,
                "message": message,
                "error": str(err),
                "user-agent": self.request.headers.get("User-Agent"),
                "request_id": self.request_uuid,
                "tenant": tenant,
            }
            errors = [str(err)]
            await handle_generic_error_response(
                self, message, errors, 400, str(err), log_data
            )
