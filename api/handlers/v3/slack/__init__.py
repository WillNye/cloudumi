from api.handlers.model_handlers import ConfigurationCrudHandler
from common.models import SlackIntegration


class SlackIntegrationConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = SlackIntegration
    _config_key = "slack"


# import os
# from slack_bolt.async_app import AsyncApp
# from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
# from fastapi import FastAPI
# import logging

# logging.basicConfig(level=logging.DEBUG)
# os.environ["SLACK_APP_TOKEN"] = "A_SECRET"
# os.environ["SLACK_BOT_TOKEN"] = "A_SECRET"

# app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))
# handler = AsyncSocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))

# @app.event({"type": "message"})
# async def receive_message(event, say):
#     await say("Hiya")

# web_app = FastAPI()

# @web_app.get("/healthcheck")
# async def healthcheck():
#     if handler.client is not None and await handler.client.is_connected():
#         return "OK"
#     return "BAD"

# @web_app.on_event('startup')
# async def start_slack_socket_conn():
#     await handler.connect_async()

# @web_app.on_event('shutdown')
# async def start_slack_socket_conn():
#     await handler.close_async()
