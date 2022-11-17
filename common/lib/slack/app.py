import asyncio
import boto3
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.oauth.installation_store.amazon_s3 import AmazonS3InstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore

from api.handlers.v2.typeahead import get_matching_identity_typahead
from common.config import config
from common.lib.iambic.git import IambicGit
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

oauth_settings = AsyncOAuthSettings(
    client_id=config.get("_global_.secrets.slack.client_id"),
    client_secret=config.get("_global_.secrets.slack.client_secret"),
    # TODO: Fix these
    scopes=scopes,
    installation_store=AmazonS3InstallationStore(
        s3_client=boto3.client("s3", region_name="us-west-2"), # TODO Configurable
        bucket_name=config.get("_global_.s3_slack_installation_store_bucket"),
        client_id=config.get("_global_.secrets.slack.client_id"),
    ),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data/states"),
    install_path="/api/v3/slack/install",
    redirect_uri_path="/api/v3/slack/oauth_redirect",
    # TODO: Replace ngrok with something more generic
    # redirect_uri="https://a340-68-4-188-30.ngrok.io/api/v3/slack/oauth_redirect",
)

slack_app = AsyncApp(
    token=config.get("_global_.secrets.slack.bot_token"),
    signing_secret=config.get("_global_.secrets.slack.signing_secret"),
    # installation_store=AmazonS3InstallationStore(
    #     s3_client=boto3.client('s3'),
    #     bucket_name=config.get("_global_.s3_slack_installation_store_bucket"),
    #     client_id=config.get("_global_.secrets.slack.client_id"),
    # ),
    oauth_settings=oauth_settings,
    process_before_response=True,
)

# Need a mapping of Slack Token to Tenant ID

async def respond_to_ack(body, ack):
    await ack(
        {
            "response_action": "clear"
        }
    )

@slack_app.command("/request_access")
async def handle_request_access_command(ack, body, logger):
    await ack()
    logger.info(body)


@slack_app.message("hello")
async def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    await say(f"Hey there <@{message['user']}>!")


async def message_alert():
    channel_id = "C045MFZ2A10"
    await slack_app.client.chat_postMessage(
        channel=channel_id,
        text="Summer has come and passed",
        blocks=unauthorized_change_sample,
    )

    await slack_app.client.chat_postMessage(
        channel=channel_id,
        text="Summer has come and passed",
        blocks=remove_unused_identities_sample,
    )


@slack_app.event("message")
async def handle_message_events(body, logger):
    logger.info(body)


@slack_app.command("/hello-noq")
async def hello(body, ack):
    await ack(f"Hi <@{body['user_id']}>!")


@slack_app.options("external_action")
async def show_options(ack, respond, payload):
    await ack()
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
    await ack(options=options)
    # await respond(options=options)


@slack_app.shortcut("request_access")
async def request_access(ack, body, client):
    # Acknowledge the command request
    await ack()
    # Call views_open with the built-in client
    await client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=request_access_to_resource_block,
    )


@slack_app.shortcut("request_permissions")
async def request_permissions(ack, body, client):
    # Acknowledge the command request
    await ack()
    # Call views_open with the built-in client
    await client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=request_permissions_to_resource_block,
    )


@slack_app.action("select_resources")
async def handle_select_resources_action(ack, body, client, logger):
    await ack()
    logger.info(body)


@slack_app.middleware  # or app.use(log_request)
async def log_request(logger, body, next):
    logger.debug(body)
    return await next()


@slack_app.event("app_mention")
async def event_test(ack, body, say, logger):
    logger.info(body)
    say("What's up?")


@slack_app.options("select_resources")
async def handle_select_resources_options(ack, respond, body, client, logger):
    # TODO: Need to get list of resources to request access to
    await ack()
    tenant = "localhost"  # TODO fix
    user = "curtis@noq.dev"
    groups = []  # Need SCIM integration?
    typeahead = await get_matching_identity_typahead(
        tenant, body["value"], user, groups
    )
    options = []
    for typeahead_entry in typeahead:
        if typeahead_entry["principal"]["principal_type"] == "AwsResource":
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": typeahead_entry["principal"]["principal_arn"],
                    },
                    "value": typeahead_entry["principal"]["principal_arn"],
                }
            )
    await ack(options=options)


# TODO: remove this?
async def handle_request_access_to_resource_long_process(respond, logger, body):
    tenant = "localhost"  # TODO fix
    # TODO: Need to pre-clone to EBS
    iambic = IambicGit(tenant)
    role_arns = [
        x["value"]
        for x in body["view"]["state"]["values"]["request_access"]["select_resources"][
            "selected_options"
        ]
    ]
    duration = int(
        body["view"]["state"]["values"]["duration"]["duration"]["selected_option"][
            "value"
        ]
    )
    justification = body["view"]["state"]["values"]["justification"]["justification"][
        "value"
    ]
    slack_user = body["user"]["username"]
    res = await iambic.create_role_access_pr(
        role_arns,
        slack_user,
        duration,
        justification,
    )

    # TODO: Identify the file associated with a role
    # TODO: Link the appropriate GitHub Username to the request
    # TODO: Submit a PR
    # TODO: Iambic auto-approve the PR based on rules in the git repo
    # TODO: Return PR URL
    res = await respond(
        {"response_action": "update", "view": request_access_to_resource_success}
    )
    print(res)
    

async def handle_request_access_to_resource_ack(ack):
    await ack(response_action="update", view=request_access_to_resource_success)
    
#@slack_app.view("request_access_to_resource")
async def handle_request_access_to_resource(body, client, logger, respond):
    # TODO: Clone known repos to shared EBS volume, logically separated by tenant
    # If repo exists, git pull
    # await ack({
    #         "response_action": "clear"
    #     })  # Respond immediately to ack to avoid timeout
    # await ack(response_action="update", view=request_access_to_resource_success)
    logger.info(body)
    # client.views_update(
    #     #token=bot_token,
    #     view_id=body['view']['id'],
    #     hash=body['view']['hash'],
    #     view=request_access_to_resource_success,
    # )
    tenant = "localhost"  # TODO fix
    # TODO: Need to pre-clone to EBS
    iambic = IambicGit(tenant)
    role_arns = [
        x["value"]
        for x in body["view"]["state"]["values"]["request_access"]["select_resources"][
            "selected_options"
        ]
    ]
    duration = int(
        body["view"]["state"]["values"]["duration"]["duration"]["selected_option"][
            "value"
        ]
    )
    justification = body["view"]["state"]["values"]["justification"]["justification"][
        "value"
    ]
    slack_user = body["user"]["username"]
    res = await iambic.create_role_access_pr(
        role_arns,
        slack_user,
        duration,
        justification,
    )
    # TODO: Identify the file associated with a role
    # TODO: Link the appropriate GitHub Username to the request
    # TODO: Submit a PR
    # TODO: Iambic auto-approve the PR based on rules in the git repo
    # TODO: Return PR URL
    # res = await respond({"response_action": "update", "view": request_access_to_resource_success})
    # TODO: Test this new view
    # await client.views_update(
    #     view_id=body["view"]["id"],
    #     hash=body["view"]["hash"],
    #     view=request_access_to_resource_success,
    # )
    # await respond("Submitted", response_type="ephemeral")
    # Send a message to the user
    role_arns_text = ", ".join(role_arns)
    pr_url = res['github_pr']
    conversation = await client.conversations_open(users=body['user']['id'])
    message = await client.chat_postMessage(
        channel=conversation['channel']['id'], 
        text=(
            f"Your request for access to {role_arns_text} has been submitted.\n\n"
            f"You may view it here: {pr_url}"
        )
    )


# def main():
#     handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
#     handler.start_async()


@slack_app.event("user_change")
async def handle_user_change_events(body, logger):
    logger.info(body)


@slack_app.event("user_status_changed")
async def handle_user_status_changed_events(body, logger):
    logger.info(body)
    
slack_app.view("request_access_to_resource")(
    ack=handle_request_access_to_resource_ack,
    lazy=[handle_request_access_to_resource]
)


# slack_app.view("request_access_to_resource")(
#     ack=handle_request_access_to_resource,
#     lazy=[handle_request_access_to_resource_long_process]
# )
