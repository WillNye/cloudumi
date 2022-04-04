from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
from common.celery_tasks.settings import synchronize_cognito_sso
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
    _config_key = None
    _identifying_keys = ["Username"]

    def _retrieve(self) -> list[dict]:
        pass

    async def _create(self, data):
        pass

    async def _delete(self, data):
        pass


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
