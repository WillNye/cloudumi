from api.handlers.model_handlers import ConfigurationCrudHandler
from common.models import ChallengeUrl


class ChallengeUrlConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = ChallengeUrl
    _config_key = "auth.challenge_url"
