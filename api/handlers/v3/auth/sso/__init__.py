import boto3

from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.config import config
from common.lib.cognito import identity
from common.models import (
    CognitoGroup,
    CognitoUser,
    GoogleOIDCSSOIDPProvider,
    OIDCSSOIDPProvider,
    SamlOIDCSSOIDPProvider,
    SSOIDPProviders,
)

LOG = config.get_logger()


class IdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _config_key = "IdentityProvider"
    _user_pool_id = None
    _user_pool_client_id = None
    _model_class = None
    _sso_idp_attr = None

    @property
    def user_pool_id(self) -> str:
        if user_pool_id := getattr(self, "_user_pool_id"):
            return user_pool_id

        user_pool_id = config.get_host_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.host
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        self._user_pool_id = user_pool_id
        return user_pool_id

    @property
    def user_pool_client_id(self) -> str:
        if user_pool_client_id := getattr(self, "_user_pool_client_id"):
            return user_pool_client_id

        user_pool_client_id = config.get_host_specific_key(
            "secrets.cognito.config.user_pool_client_id", self.ctx.host
        )
        if not user_pool_client_id:
            raise ValueError("Cognito user pool client id not configured")

        self._user_pool_client_id = user_pool_client_id
        return user_pool_client_id

    def _retrieve(self) -> dict:
        cognito_idp = boto3.client("cognito-idp", region_name=config.region)

        try:
            sso_idp_provider = identity.get_identity_providers(self.user_pool_id)
        except cognito_idp.exceptions.ResourceNotFoundException:
            raise ValueError

        if (
            self._sso_idp_attr
        ):  # If a specific identity provider was specified only provide that one
            provider_val = getattr(sso_idp_provider, self._sso_idp_attr, None)
            return provider_val.dict() if provider_val else {}

        return sso_idp_provider.dict()

    async def _create(self, data):
        if not self._sso_idp_attr:  # Upsert all the things
            sso_idp_provider = self._model_class(**data)
        else:
            sso_idp_provider = SSOIDPProviders()
            setattr(sso_idp_provider, self._sso_idp_attr, self._model_class(**data))

        return identity.upsert_identity_provider(
            self.user_pool_id, self.user_pool_client_id, sso_idp_provider
        )

    async def _delete(self) -> bool:
        pass


class GoogleOidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = GoogleOIDCSSOIDPProvider
    _sso_idp_attr = "google"


class SamlOidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SamlOIDCSSOIDPProvider
    _sso_idp_attr = "saml"


class OidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = OIDCSSOIDPProvider
    _sso_idp_attr = "oidc"


class SsoIdpProviderConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SSOIDPProviders


class CognitoUserCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoUser
    _config_key = "Unused"
    _identifying_keys = ["Username"]
    _user_pool_id = None

    @property
    def user_pool_id(self) -> str:
        if user_pool_id := getattr(self, "_user_pool_id"):
            return user_pool_id

        user_pool_id = config.get_host_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.host
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        self._user_pool_id = user_pool_id
        return user_pool_id

    def _retrieve(self) -> list[dict]:
        users = list()
        for user in identity.get_identity_users(self.user_pool_id):
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword")
            users.append(user_dict)

        return users

    async def _create(self, data) -> CognitoUser:
        cognito_idp = boto3.client("cognito-idp", region_name=config.region)

        try:
            # Update the resource
            cognito_user = self._model_class(**data)
            cognito_user.Groups = [
                x
                for x in identity.get_identity_user_groups(
                    self.user_pool_id, cognito_user
                )
            ]
            identity.upsert_identity_user_group(self.user_pool_id, cognito_user)
        except cognito_idp.exceptions.UserNotFoundException:
            # Resource doesn't exist, so create it
            return identity.create_identity_user(
                self.user_pool_id, self._model_class(**data)
            )

    async def _delete(self, data) -> bool:
        return identity.delete_identity_user(
            self.user_pool_id, self._model_class(**data)
        )


class CognitoGroupCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoGroup
    _config_key = "Unused"
    _identifying_keys = ["GroupName"]
    _user_pool_id = None

    @property
    def user_pool_id(self) -> str:
        if user_pool_id := getattr(self, "_user_pool_id"):
            return user_pool_id

        user_pool_id = config.get_host_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.host
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        self._user_pool_id = user_pool_id
        return user_pool_id

    def _retrieve(self) -> list[dict]:
        return [
            group.dict() for group in identity.get_identity_groups(self.user_pool_id)
        ]

    async def _create(self, data) -> CognitoGroup:
        cognito_idp = boto3.client("cognito-idp", region_name=config.region)
        try:
            # Update the resource
            cognito_group = identity.get_identity_group(
                self.user_pool_id, data["GroupName"]
            )
            if (
                description := data.get("Description")
            ) and description != cognito_group.Description:
                cognito_group.Description = description
                return identity.update_identity_group(self.user_pool_id, cognito_group)

        except cognito_idp.exceptions.ResourceNotFoundException:
            # Resource doesn't exist, so create it
            return identity.create_identity_group(
                self.user_pool_id, self._model_class(**data)
            )

    async def _delete(self, data) -> bool:
        return identity.delete_identity_group(
            self.user_pool_id, self._model_class(**data)
        )
