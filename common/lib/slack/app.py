import datetime
import logging
import time
import zlib
from collections import defaultdict
from functools import partial
from typing import Optional
from uuid import uuid4

import jmespath
import ujson as json
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
from common.iambic_request.models import GitHubPullRequest
from common.iambic_request.request_crud import create_request
from common.iambic_request.utils import get_iambic_repo
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.iambic.git import IambicGit
from common.lib.redis import RedisHandler
from common.lib.slack.models import (
    BOTS_TABLE,
    INSTALLATIONS_TABLE,
    OAUTH_STATES_TABLE,
    get_slack_bot,
    get_slack_bot_authorization,
)
from common.lib.slack.workflows import (
    remove_unused_identities_sample,
    request_access_to_resource_block,
    request_access_to_resource_success,
    request_permissions_to_resource_block,
    self_service_step_1_option_selection,
    self_service_submission_success,
    unauthorized_change_sample,
)
from common.models import IambicTemplateChange

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
    installation_store=installation_store,
    scopes=scopes,
    user_scopes=scopes,
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
    # logger.info(body)


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
    # TODO: we must figure out the provider so we know what to Typahead against
    # But the provider is empty
    provider = body["view"]["state"]  # ['values'].get("provider_dropdown")

    red = RedisHandler().redis_sync(tenant)
    token = body["token"]
    hash = body["view"]["hash"]
    slack_app_type = red.get(f"{tenant}_SLACK_APP_TYPE_{token}_{hash}")
    red.get(f"{tenant}_SLACK_APP_TYPE_{token}_{hash}")
    redis_key = config.get_tenant_specific_key(
        "cache_organization_structure.redis.key.org_structure_key",
        tenant,
        f"{tenant}_IAMBIC_TEMPLATES",
    )
    template_dicts = await retrieve_json_data_from_redis_or_s3(
        redis_key=redis_key,
        tenant=tenant,
    )
    if slack_app_type:
        # Old filter: f"[?template_type=='NOQ::Google::Group' && contains(properties.name, '{body['value']}')]",
        res = jmespath.search(
            # f"[?contains(properties.name, '{body['value']}')]",
            f"[?template_type=='{slack_app_type}' && contains(properties.name, '{body['value']}')]",
            template_dicts,
        )
    else:
        res = jmespath.search(
            f"[?contains(properties.name, '{body['value']}')]",
            template_dicts,
        )
    friendly_names = {
        "NOQ::AWS::IAM::Group": "AWS IAM Groups",
        "NOQ::AWS::IAM::ManagedPolicy": "AWS IAM Managed Policies",
        "NOQ::AWS::IAM::Role": "AWS IAM Roles",
        "NOQ::AWS::IAM::Users": "AWS IAM Users",
        "NOQ::AWS::IdentityCenter::PermissionSet": "AWS Permission Sets",
        "NOQ::Google::Group": "Google Groups",
        "NOQ::Okta::App": "Okta Apps",
        "NOQ::Okta::Group": "Okta Groups",
        "NOQ::Okta::User": "Okta Users",
    }
    option_groups = defaultdict(list)
    for typeahead_entry in res:
        template_type = typeahead_entry["template_type"]
        friendly_name = friendly_names.get(template_type, template_type)
        if not option_groups.get(friendly_name):
            option_groups[friendly_name] = {
                "label": {"type": "plain_text", "text": friendly_name},
                "options": [],
            }

        smaller_string = f'{typeahead_entry["template_type"]}|{typeahead_entry["repo_name"]}|{typeahead_entry["repo_relative_file_path"]}'

        option_groups[friendly_name]["options"].append(
            {
                "text": {
                    "type": "plain_text",
                    "text": typeahead_entry["properties"]["name"],
                },
                # Warning: Slack docs specify the max length of options value is 75 characters
                # but it is actually larger. Slack will not give you an error if this is exceeded.
                "value": smaller_string,
            }
        )
    option_groups = [v for _, v in option_groups.items()]
    option_groups_formatted = {
        "option_groups": option_groups,
    }
    res = await ack(option_groups_formatted)


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
    pass
    # logger.info(body)


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


async def handle_select_resources_tenant(ack, body, client, logger, tenant):
    await ack()


@slack_app.middleware  # or app.use(log_request)
async def log_request(logger, body, next):
    # logger.debug(body)
    return await next()


def create_log_request_handler(tenant):
    async def _log_request(logger, body, next):
        # logger.debug(body)
        return await next()

    return _log_request


async def handle_request_access_to_resource_ack(ack):
    await ack(response_action="update", view=request_access_to_resource_success)


# @slack_app.view("request_access_to_resource")
async def handle_request_access_to_resource_tenant(
    body, client, logger, respond, tenant, tenant_slack_app
):
    # TODO: Use IambicGit to make a request
    # TODO: Convert Slack username to e-mail
    user = body["user"]["username"]
    justification = "justification"  # TODO: Get from body
    iambic = IambicGit(tenant)
    iambic_repo = await get_iambic_repo(tenant)
    # TODO: Figure out how to get user info
    # user_email = await tenant_slack_app.client.users_info(user=body["user"]["id"])
    user_info = await client.users_info(user=body["user"]["id"])
    user_email = user_info._initial_data["user"]["profile"]["email"]
    selected_options = body["view"]["state"]["values"]["request_access"][
        "select_resources"
    ]["selected_options"]
    duration = body["view"]["state"]["values"]["duration"]["duration"][
        "selected_option"
    ]["value"]
    template_changes = []
    for option in selected_options:
        value = option["value"].split("|")
        if len(value) != 3:
            raise Exception("Invalid selected options value")

        template_type = value[0]
        repo_name = value[1]
        path = value[2][1:]
        if template_type == "NOQ::Google::Group":
            template = await iambic.google_add_user_to_group(
                template_type, repo_name, path, user_email, duration
            )
        elif template_type == "NOQ::Okta::Group":
            template = await iambic.okta_add_user_to_group(
                template_type, repo_name, path, user_email, duration
            )
        elif template_type == "NOQ::Okta::App":
            template = await iambic.okta_add_user_to_app(
                template_type, repo_name, path, user, duration
            )

        template_changes.append(
            IambicTemplateChange(path=path, body=template.get_body(exclude_unset=False))
        )
    if not template_changes:
        await respond(
            response_action="errors",
            errors={
                "select_resources": "You must select at least one resource to request access to"
            },
        )
        return

    request_id = str(uuid4())
    pull_request_id = None
    request_pr = GitHubPullRequest(
        access_token=iambic_repo.access_token,
        repo_name=iambic_repo.repo_name,
        tenant=tenant,
        request_id=request_id,
        requested_by=user_email,
        merge_on_approval=iambic_repo.merge_on_approval,
        pull_request_id=pull_request_id,
    )

    await request_pr.create_request(justification, template_changes)
    request_details = await request_pr.get_request_details()
    pr_url = request_details["pull_request_url"]
    # logger.info(body)
    # res = await create_request(tenant, user, justification, template_changes)
    # role_arns = [
    #     x["value"]
    #     for x in body["view"]["state"]["values"]["request_access"]["select_resources"][
    #         "selected_options"
    #     ]
    # ]
    # duration = int(
    #     body["view"]["state"]["values"]["duration"]["duration"]["selected_option"][
    #         "value"
    #     ]
    # )
    # justification = body["view"]["state"]["values"]["justification"]["justification"][
    #     "value"
    # ]
    # slack_user = body["user"]["username"]
    # res = await iambic.create_role_access_pr(
    #     role_arns,
    #     slack_user,
    #     duration,
    #     justification,
    # )
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
    # role_arns_text = ", ".join(role_arns)
    # pr_url = res["github_pr"]
    # conversation = await client.conversations_open(users=body["user"]["id"])
    channel_id = "C045MFZ2A10"
    await client.chat_postMessage(
        channel=channel_id,
        text=(
            f"A request for access has been submitted.\n\n"
            f"You may view it here: {pr_url}"
        ),
    )

    view_id = body["view"]["id"]
    # Update view
    await client.views_update(
        view_id=view_id,
        view=self_service_submission_success.replace(
            "{{pull_request_url}}", pr_url
        ),  # TODO change
    )
    print("here")  # TODO REMOVE


@slack_app.event("user_change")
async def handle_user_change_events(body, logger):
    pass
    # logger.info(body)


@slack_app.event("user_status_changed")
async def handle_user_status_changed_events(body, logger):
    pass
    # logger.info(body)


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


async def request_access_step_1_tenant(ack, body, client, tenant):
    # Acknowledge the command request
    await ack()
    # Call views_open with the built-in client
    await client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view=self_service_step_1_option_selection,
    )


def render_step_2_request_access():
    return {
        "type": "modal",
        "callback_id": "modal_step_2",
        "title": {"type": "plain_text", "text": "Request Access"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "Please fill out the form below to request access.",
                },
            }
        ],
    }


def render_step_2_request_new_cloud_permissions():
    return {
        "type": "modal",
        "callback_id": "modal_step_2",
        "title": {"type": "plain_text", "text": "Cloud Permissions"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "Please fill out the form below to request new cloud permissions.",
                },
            }
        ],
    }


def render_step_2_create_cloud_identity_or_resource():
    return {
        "type": "modal",
        "callback_id": "modal_step_2",
        "title": {"type": "plain_text", "text": "Create a Cloud Identity or Resource"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "Please fill out the form below to create a cloud identity or resource.",
                },
            }
        ],
    }


async def handle_select_app_type(ack, logger, body, client, respond, tenant):
    # Acknowledge the action to confirm receipt
    await ack()
    red = RedisHandler().redis_sync(tenant)
    # Token is unique to the user and workspace
    token = body["token"]
    # Hash is
    hash = body["view"]["hash"]
    # Get the value of the selected radio button
    selected_option = body["actions"][0]["selected_option"]["value"]
    # Store in a temporary redis key (Really Slack?)
    red.setex(f"{tenant}_SLACK_APP_TYPE_{token}_{hash}", 300, selected_option)


async def handle_request_access_step_1_callback(
    ack, logger, body, client, respond, tenant
):
    # Acknowledge the action to confirm receipt
    await ack()

    # Get the value of the selected radio button
    selected_option = body["view"]["state"]["values"]["self_service_step_1_block"][
        "self_service_step_1_option_selection"
    ]["selected_option"]["value"]

    # Render step 2 conditionally based on the selected option
    if selected_option == "request_access_to_identity":
        view = request_access_to_resource_block
    elif selected_option == "request_permissions_for_identity":
        view = render_step_2_request_new_cloud_permissions()
    elif selected_option == "create_cloud_identity_or_resource":
        view = render_step_2_create_cloud_identity_or_resource()
    else:
        raise Exception("Invalid option selected")
    await ack(response_action="update", view=view)


async def handle_user_change_events(body, logger, tenant):
    pass


async def get_slack_app_for_tenant(tenant, enterprise_id, team_id, app_id):
    tenant_slack_app = AsyncApp(
        name=tenant,
        logger=logger,
        installation_store=installation_store,
        # token=config.get("_global_.secrets.slack.bot_token"),
        signing_secret=config.get("_global_.secrets.slack.signing_secret"),
        process_before_response=True,
        # authorize=get_slack_bot_authorization,
    )
    tenant_slack_app.use(create_log_request_handler(tenant))
    # tenant_slack_app.middleware(partial(log_request_tenant, tenant=tenant))

    tenant_slack_app.message("hello_tenant")(
        ack=handle_ack,
        lazy=[partial(message_hello_tenant, tenant=tenant)],
    )

    tenant_slack_app.action("select_resources")(
        ack=handle_ack,
        lazy=[partial(handle_select_resources_tenant, tenant=tenant)],
    )

    tenant_slack_app.options("select_resources")(
        partial(handle_select_resources_options_tenant, tenant=tenant)
    )

    tenant_slack_app.view("request_access_to_resource")(
        ack=handle_request_access_to_resource_ack,
        lazy=[
            partial(
                handle_request_access_to_resource_tenant,
                tenant=tenant,
                tenant_slack_app=tenant_slack_app,
            )
        ],
    )
    tenant_slack_app.shortcut("noq")(
        ack=handle_ack,
        lazy=[partial(request_access_step_1_tenant, tenant=tenant)],
    )
    tenant_slack_app.command("/noq")(
        ack=handle_ack,
        lazy=[partial(request_access_step_1_tenant, tenant=tenant)],
    )
    tenant_slack_app.event("user_change")(
        partial(handle_user_change_events, tenant=tenant)
    )
    tenant_slack_app.view("self_service_step_1")(
        partial(handle_request_access_step_1_callback, tenant=tenant)
    )
    tenant_slack_app.view_submission("self_service_step_1")(
        partial(handle_request_access_step_1_callback, tenant=tenant)
    )

    tenant_slack_app.action("select_app_type")(
        partial(handle_select_app_type, tenant=tenant)
    )
    tenant_slack_app.view("request_success")(handle_ack)
    return tenant_slack_app
