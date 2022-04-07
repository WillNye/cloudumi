import boto3

from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.celery_tasks.settings import synchronize_cognito_sso
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


class GoogleOidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = GoogleOIDCSSOIDPProvider
    _config_key = "secrets.auth.google"
    _triggers = [synchronize_cognito_sso]


class SamlOidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SamlOIDCSSOIDPProvider
    _config_key = "secrets.auth.saml"
    _triggers = [synchronize_cognito_sso]


class OidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = OIDCSSOIDPProvider
    _config_key = "secrets.auth.oidc"
    _triggers = [synchronize_cognito_sso]


class SsoIdpProviderConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SSOIDPProviders
    _config_key = "secrets.auth"


class CognitoCrudHandler(MultiItemConfigurationCrudHandler):
    _config_key = "Unused"
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


class CognitoUserCrudHandler(CognitoCrudHandler):
    _model_class = CognitoUser
    _identifying_keys = ["Username"]

    def _retrieve(self) -> list[dict]:
        users = list()
        for user in identity.get_identity_users(self.user_pool_id):
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword")
            for attr in user_dict.get("Attributes", []):
                if attr["Name"] == "email":
                    user_dict["Username"] = attr["Value"]
                    break

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


class CognitoGroupCrudHandler(CognitoCrudHandler):
    _model_class = CognitoGroup
    _identifying_keys = ["GroupName"]

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
