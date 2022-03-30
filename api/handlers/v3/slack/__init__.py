from api.handlers.model_handlers import ConfigurationCrudHandler
from common.models import SlackIntegration


class SlackIntegrationConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SlackIntegration
    _config_key = "slack"
