from api.handlers.model_handlers import (
    ConfigurationCrudHandler,
    MultiItemConfigurationCrudHandler,
)
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


class SamlOidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SamlOIDCSSOIDPProvider
    _config_key = "secrets.auth.saml"


class OidcIdpConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = OIDCSSOIDPProvider
    _config_key = "secrets.auth.oidc"


class SsoIdpProviderConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SSOIDPProviders
    _config_key = "secrets.auth"


class CognitoUserCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoUser
    _config_key = "aws.cognito.accounts.users"


class CognitoGroupCrudHandler(MultiItemConfigurationCrudHandler):
    _model_class = CognitoGroup
    _config_key = "aws.cognito.accounts.groups"
