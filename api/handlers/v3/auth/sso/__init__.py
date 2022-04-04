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


class CognitoUserCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoUser
    _config_key = "Unused"
    _identifying_keys = ["Username"]

    @property
    def user_pool_id(self) -> str:
        user_pool_id = config.get_host_specific_key(
            "secrets.cognito.config.user_pool_id", self.ctx.host
        )
        if not user_pool_id:
            raise ValueError("Cognito user pool id not configured")

        return user_pool_id

    def _retrieve(self) -> list[dict]:
        users = list()
        for user in identity.get_identity_users(self.user_pool_id):
            user_dict: dict = user.dict()
            user_dict.pop("TemporaryPassword")
            users.append(user_dict)

        return users

    async def _create(self, data) -> CognitoUser:
        return identity.create_identity_user(
            self.user_pool_id, self._model_class(**data)
        )

    async def _delete(self, data) -> bool:
        return identity.delete_identity_user(
            self.user_pool_id, self._model_class(**data)
        )


class CognitoGroupCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoGroup
    _config_key = "secrets.cognito.accounts.groups"
    _identifying_keys = ["GroupName"]

    def _retrieve(self) -> list[dict]:
        pass

    async def _create(self, data):
        pass

    async def _delete(self, data):
        pass
