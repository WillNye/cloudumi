import datetime
import logging
import time
from functools import partial
from typing import Optional
from uuid import uuid4

import jmespath
from databases import Database
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.oauth.installation_store import Bot, Installation
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.state_store.async_state_store import AsyncOAuthStateStore
from sqlalchemy import MetaData, Table, and_, desc

from api.handlers.v2.typeahead import get_matching_identity_typahead
from common.config import config, globals
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.iambic.git import IambicGit
from common.lib.slack.models import BOTS_TABLE, INSTALLATIONS_TABLE, OAUTH_STATES_TABLE
from common.lib.slack.workflows import (
    remove_unused_identities_sample,
    request_access_to_resource_block,
    request_access_to_resource_success,
    request_permissions_to_resource_block,
    unauthorized_change_sample,
)

scopes = """app_mentions:read,channels:history,channels:join,channels:read,chat:write,chat:write.public,emoji:read,groups:history,groups:read,groups:write,im:history,im:read,im:write,mpim:history,mpim:read,mpim:write,pins:read,pins:write,reactions:read,reactions:write,users:read,users:read.email,channels:manage,chat:write.customize,dnd:read,files:read,files:write,links:read,links:write,metadata.message:read,usergroups:read,usergroups:write,users.profile:read,users:write""".split(
    ","
)

logger = logging.getLogger(__name__)


class AsyncSQLAlchemyInstallationStore(AsyncInstallationStore):
    database_url: str
    client_id: str
    metadata: MetaData
    installations: Table
    bots: Table

    def __init__(
        self,
        client_id: str,
        database_url: str,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.client_id = client_id
        self.database_url = database_url
        self._logger = logger
        self.metadata = MetaData()
        self.installations = INSTALLATIONS_TABLE
        self.bots = BOTS_TABLE

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    async def async_save(self, installation: Installation):
        async with Database(self.database_url) as database:
            async with database.transaction():
                i = installation.to_dict()
                i["client_id"] = self.client_id
                await database.execute(self.installations.insert(), i)
                b = installation.to_bot().to_dict()
                b["client_id"] = self.client_id
                await database.execute(self.bots.insert(), b)

    async def async_find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool],
    ) -> Optional[Bot]:
        c = self.bots.c
        query = (
            self.bots.select()
            .where(
                and_(
                    c.enterprise_id == enterprise_id,
                    c.team_id == team_id,
                    c.is_enterprise_install == is_enterprise_install,
                )
            )
            .order_by(desc(c.installed_at))
            .limit(1)
        )
        async with Database(self.database_url) as database:
            result = await database.fetch_one(query)
            if result:
                return Bot(
                    app_id=result["app_id"],
                    enterprise_id=result["enterprise_id"],
                    team_id=result["team_id"],
                    bot_token=result["bot_token"],
                    bot_id=result["bot_id"],
                    bot_user_id=result["bot_user_id"],
                    bot_scopes=result["bot_scopes"],
                    installed_at=result["installed_at"],
                )
            else:
                return None


class AsyncSQLAlchemyOAuthStateStore(AsyncOAuthStateStore):
    database_url: str
    expiration_seconds: int
    metadata: MetaData
    oauth_states: Table

    def __init__(
        self,
        *,
        expiration_seconds: int,
        database_url: str,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.expiration_seconds = expiration_seconds
        self.database_url = database_url
        self._logger = logger
        self.metadata = MetaData()
        self.oauth_states = OAUTH_STATES_TABLE

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    async def async_issue(self) -> str:
        state: str = str(uuid4())
        now = datetime.datetime.utcfromtimestamp(time.time() + self.expiration_seconds)
        async with Database(self.database_url) as database:
            await database.execute(
                self.oauth_states.insert(), {"state": state, "expire_at": now}
            )
            return state

    async def async_consume(self, state: str) -> bool:
        try:
            async with Database(self.database_url) as database:
                async with database.transaction():
                    c = self.oauth_states.c
                    query = self.oauth_states.select().where(
                        and_(c.state == state, c.expire_at > datetime.datetime.utcnow())
                    )
                    row = await database.fetch_one(query)
                    self.logger.debug(f"consume's query result: {row}")
                    await database.execute(
                        self.oauth_states.delete().where(c.id == row["id"])
                    )
                    return True
            return False
        except Exception as e:
            message = f"Failed to find any persistent data for state: {state} - {e}"
            self.logger.warning(message)
            return False


database_url = globals.ASYNC_PG_CONN_STR

installation_store = AsyncSQLAlchemyInstallationStore(
    client_id=config.get("_global_.secrets.slack.client_id"),
    database_url=database_url,
    logger=logger,
)

oauth_state_store = AsyncSQLAlchemyOAuthStateStore(
    expiration_seconds=120,
    database_url=database_url,
    logger=logger,
)

oauth_settings = AsyncOAuthSettings(
    client_id=config.get("_global_.secrets.slack.client_id"),
    client_secret=config.get("_global_.secrets.slack.client_secret"),
    state_store=oauth_state_store,
    scopes=scopes,
    install_path="/api/v3/slack/install",
    redirect_uri_path="/api/v3/slack/oauth_redirect",
)

slack_app = AsyncApp(
    logger=logger,
    installation_store=installation_store,
    # token=config.get("_global_.secrets.slack.bot_token"),
    signing_secret=config.get("_global_.secrets.slack.signing_secret"),
    oauth_settings=oauth_settings,
    process_before_response=True,
)


async def respond_to_ack(body, ack):
    await ack({"response_action": "clear"})


@slack_app.command("/request_access")
async def handle_request_access_command(ack, body, logger):
    await ack()
    logger.info(body)


@slack_app.message("hello")
async def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    await say(f"Hey there <@{message['user']}>!")


async def message_hello_tenant(body, client, logger, respond, say, context, tenant):
    # say() sends a message to the channel where the event was triggered
    await say(f"Hey there {tenant}!")


async def handle_select_resources_options_tenant(
    ack, respond, body, client, logger, tenant
):
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_IAMBIC_TEMPLATES",
    )
    template_dicts = await retrieve_json_data_from_redis_or_s3(
        template_dicts,
        redis_key=redis_key,
        tenant=tenant,
    )

    res = jmespath.search(
        f"[?template_type=='NOQ::Google::Group' && contains(properties.name, '{body['value']}')]",
        template_dicts,
    )
    options = []
    for typeahead_entry in res:
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


# @slack_app.action("select_resources")
# async def handle_select_resources_action(ack, body, client, logger):
#     await ack()
#     logger.info(body)


@slack_app.middleware  # or app.use(log_request)
async def log_request(logger, body, next):
    logger.debug(body)
    return await next()


def create_log_request_handler(tenant):
    async def _log_request(logger, body, next):
        logger.debug(body)
        return await next()

    return _log_request


async def handle_request_access_to_resource_ack(ack):
    await ack(response_action="update", view=request_access_to_resource_success)


# @slack_app.view("request_access_to_resource")
async def handle_request_access_to_resource_tenant(
    body, client, logger, respond, tenant
):
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
    pr_url = res["github_pr"]
    conversation = await client.conversations_open(users=body["user"]["id"])
    await client.chat_postMessage(
        channel=conversation["channel"]["id"],
        text=(
            f"Your request for access to {role_arns_text} has been submitted.\n\n"
            f"You may view it here: {pr_url}"
        ),
    )


@slack_app.event("user_change")
async def handle_user_change_events(body, logger):
    logger.info(body)


@slack_app.event("user_status_changed")
async def handle_user_status_changed_events(body, logger):
    logger.info(body)


# slack_app.view("request_access_to_resource")(
#     ack=handle_request_access_to_resource_ack, lazy=[handle_request_access_to_resource]
# )


async def handle_ack(ack):
    await ack()


async def request_access_tenant(ack, body, client, tenant):
    # Acknowledge the command request
    await ack()
    # Call views_open with the built-in client
    await client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=request_access_to_resource_block,
    )


async def get_slack_app_for_tenant(tenant):
    tenant_slack_app = AsyncApp(
        name=tenant,
        logger=logger,
        installation_store=installation_store,
        # token=config.get("_global_.secrets.slack.bot_token"),
        signing_secret=config.get("_global_.secrets.slack.signing_secret"),
        oauth_settings=oauth_settings,
        process_before_response=True,
    )
    tenant_slack_app.use(create_log_request_handler(tenant))
    # tenant_slack_app.middleware(partial(log_request_tenant, tenant=tenant))

    tenant_slack_app.message("hello_tenant")(
        ack=handle_ack,
        lazy=[partial(message_hello_tenant, tenant=tenant)],
    )

    tenant_slack_app.options("select_resources")(
        ack=handle_ack,
        lazy=[partial(handle_select_resources_options_tenant, tenant=tenant)],
    )

    tenant_slack_app.view("request_access_to_resource")(
        ack=handle_request_access_to_resource_ack,
        lazy=[partial(handle_request_access_to_resource_tenant, tenant=tenant)],
    )
    tenant_slack_app.shortcut("request_access")(
        ack=handle_ack,
        lazy=[partial(request_access_tenant, tenant=tenant)],
    )
    return tenant_slack_app
