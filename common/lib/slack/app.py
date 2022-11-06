import boto3
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store.amazon_s3 import AmazonS3InstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore

from common.config import config
from common.lib.slack.workflows import (
    remove_unused_identities_sample,
    request_access_to_resource_block,
    request_access_to_resource_success,
    request_permissions_to_resource_block,
    unauthorized_change_sample,
)

# We get a Slack access token and authorization token for each tenant
# TODO: https://stackoverflow.com/questions/69638910/app-architecture-for-integrating-slack-api-with-a-multi-tenant-silo-model-deploy
# Initializes your app with your bot token and socket mode handler
# TODO: Why doesn't this respond to shortcut?

# Steps: Make sure we create a private versioned bucket for this with logging
# Make sure AWS Secrets Manager is updated with slack secrets like dev is
# Make sure SaaS role has s3 rw to state buckets
# Redirect URI must be a subdirectory of the app's redirect uri

# TODO: Install URI:
# https://slack.com/oauth/v2/authorize?client_id=2599804276914.4178506792386&scope=app_mentions:read,channels:history,channels:join,channels:manage,channels:read,chat:write,chat:write.customize,chat:write.public,commands,dnd:read,emoji:read,files:read,files:write,groups:history,groups:read,groups:write,im:history,im:read,im:write,metadata.message:read,mpim:history,mpim:read,mpim:write,pins:read,pins:write,reactions:read,reactions:write,users:read,users:read.email,dnd:read,files:read,files:write,links:read,links:write,metadata.message:read,usergroups:read,usergroups:write,users.profile:read,users:write,commands&user_scope=&state=corp_noq_dev

scopes = """app_mentions:read,channels:history,channels:join,channels:read,chat:write,chat:write.public,emoji:read,groups:history,groups:read,groups:write,im:history,im:read,im:write,mpim:history,mpim:read,mpim:write,pins:read,pins:write,reactions:read,reactions:write,users:read,users:read.email,channels:manage,chat:write.customize,dnd:read,files:read,files:write,links:read,links:write,metadata.message:read,usergroups:read,usergroups:write,users.profile:read,users:write""".split(
    ","
)

# https://slack.com/oauth/v2/authorize?client_id=2599804276914.4178506792386&scope=app_mentions:read,channels:history,channels:join,channels:read,chat:write,chat:write.public,emoji:read,groups:history,groups:read,groups:write,im:history,im:read,im:write,mpim:history,mpim:read,mpim:write,pins:read,pins:write,reactions:read,reactions:write,users:read,users:read.email,channels:manage,chat:write.customize,dnd:read,files:read,files:write,links:read,links:write,metadata.message:read,usergroups:read,usergroups:write,users.profile:read,users:write,commands&user_scope=&state=corp_noq_dev


# TODO: Encrypt / verify uri in state.

oauth_settings = OAuthSettings(
    client_id=config.get("_global_.secrets.slack.client_id"),
    client_secret=config.get("_global_.secrets.slack.client_secret"),
    # TODO: Fix these
    scopes=scopes,
    installation_store=AmazonS3InstallationStore(
        s3_client=boto3.client("s3"),
        bucket_name=config.get("_global_.s3_slack_installation_store_bucket"),
        client_id=config.get("_global_.secrets.slack.client_id"),
    ),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data/states"),
    install_path="/api/v3/slack/install",
    redirect_uri_path="/api/v3/slack/oauth_redirect",
    # TODO: Replace ngrok with something more generic
    redirect_uri="https://068f-68-4-188-30.ngrok.io/api/v3/slack/oauth_redirect",
)

slack_app = App(
    token=config.get("_global_.secrets.slack.bot_token"),
    signing_secret=config.get("_global_.secrets.slack.signing_secret"),
    # installation_store=AmazonS3InstallationStore(
    #     s3_client=boto3.client('s3'),
    #     bucket_name=config.get("_global_.s3_slack_installation_store_bucket"),
    #     client_id=config.get("_global_.secrets.slack.client_id"),
    # ),
    oauth_settings=oauth_settings,
)

# Need a mapping of Slack Token to Tenant ID


@slack_app.command("/request_access")
def handle_request_access_command(ack, body, logger):
    ack()
    logger.info(body)


@slack_app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(f"Hey there <@{message['user']}>!")


def message_alert():
    channel_id = "C045MFZ2A10"
    slack_app.client.chat_postMessage(
        channel=channel_id,
        text="Summer has come and passed",
        blocks=unauthorized_change_sample,
    )

    slack_app.client.chat_postMessage(
        channel=channel_id,
        text="Summer has come and passed",
        blocks=remove_unused_identities_sample,
    )


@slack_app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


@slack_app.command("/hello-noq")
def hello(body, ack):
    ack(f"Hi <@{body['user_id']}>!")


@slack_app.options("external_action")
def show_options(ack, payload):
    options = [
        {
            "text": {"type": "plain_text", "text": "Option 1"},
            "value": "1-1",
        },
        {
            "text": {"type": "plain_text", "text": "Option 2"},
            "value": "1-2",
        },
    ]
    keyword = payload.get("value")
    if keyword is not None and len(keyword) > 0:
        options = [o for o in options if keyword in o["text"]["text"]]
    ack(options=options)


@slack_app.shortcut("request_access")
def request_access(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=request_access_to_resource_block,
    )


@slack_app.shortcut("request_permissions")
def request_permissions(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=request_permissions_to_resource_block,
    )


@slack_app.action("select_resources")
def handle_select_resources_action(ack, body, client, logger):
    ack()
    logger.info(body)


@slack_app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    logger.debug(body)
    return next()


@slack_app.event("app_mention")
def event_test(ack, body, say, logger):
    logger.info(body)
    say("What's up?")


@slack_app.options("select_resources")
def handle_select_resources_options(ack, body, client, logger):
    # TODO: Need to get list of resources to request access to

    ack(
        options=[
            {"text": {"type": "plain_text", "text": "role1"}, "value": "role1"},
            {"text": {"type": "plain_text", "text": "role2"}, "value": "role2"},
            {"text": {"type": "plain_text", "text": "role3"}, "value": "role3"},
        ]
    )


@slack_app.view("request_access_to_resource")
def handle_request_access_to_resource(ack, body, client, logger):
    ack({"response_action": "update", "view": request_access_to_resource_success})
    logger.info(body)
    # client.views_update(
    #     #token=bot_token,
    #     view_id=body['view']['id'],
    #     hash=body['view']['hash'],
    #     view=request_access_to_resource_success,
    # )


# def main():
#     handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
#     handler.start_async()


@slack_app.event("user_change")
def handle_user_change_events(body, logger):
    logger.info(body)


@slack_app.event("user_status_changed")
def handle_user_status_changed_events(body, logger):
    logger.info(body)
