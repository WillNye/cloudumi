import datetime
import logging
import re
import time
from collections import defaultdict
from functools import partial
from typing import Optional
from uuid import uuid4

import jq
import ujson as json
from policyuniverse.expander_minimizer import _expand_wildcard_action
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.errors import SlackApiError
from slack_sdk.oauth.installation_store import Bot, Installation
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.state_store.async_state_store import AsyncOAuthStateStore
from sqlalchemy import MetaData, Table, and_, desc
from sqlalchemy.sql import insert, select

from common.config import config, globals
from common.config.globals import ASYNC_PG_SESSION
from common.config.tenant_config import TenantConfig
from common.iambic_request.models import GitHubPullRequest
from common.iambic_request.request_crud import create_request
from common.iambic_request.utils import get_iambic_pr_instance, get_iambic_repo
from common.lib.asyncio import aio_wrapper
from common.lib.aws.typeahead_cache import get_all_resource_arns
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.change_request import _get_policy_sentry_access_level_actions
from common.lib.iambic.git import IambicGit
from common.lib.redis import RedisHandler
from common.lib.slack.models import BOTS_TABLE, INSTALLATIONS_TABLE, OAUTH_STATES_TABLE
from common.lib.slack.workflows import (
    friendly_resource_type_names,
    generate_self_service_step_2_app_group_access,
    get_self_service_submission_success_blocks,
    request_access_to_resource_block,
    request_access_to_resource_success,
    request_permissions_to_resource_block,
    select_desired_permissions_modal,
    self_service_permissions_review_blocks,
    self_service_request_permissions_step_2_option_selection,
    self_service_step_1_blocks,
    self_service_submission_success,
    update_or_remove_tags_modal,
)
from common.lib.yaml import yaml
from common.models import IambicTemplateChange
from common.tenants.models import Tenant

log = config.get_logger()
scopes = """app_mentions:read,channels:history,channels:join,channels:read,chat:write,chat:write.public,emoji:read,groups:history,groups:read,groups:write,im:history,im:read,im:write,mpim:history,mpim:read,mpim:write,pins:read,pins:write,reactions:read,reactions:write,users:read,users:read.email,channels:manage,chat:write.customize,dnd:read,files:read,files:write,links:read,links:write,metadata.message:read,usergroups:read,usergroups:write,users.profile:read,users:write""".split(
    ","
)

GLOBAL_SLACK_APP = None


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
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                i = installation.to_dict()
                i["client_id"] = self.client_id
                stmt = insert(self.installations).values(**i)
                await session.execute(stmt)
                b = installation.to_bot().to_dict()
                b["client_id"] = self.client_id
                stmt = insert(self.bots).values(**b)
                await session.execute(stmt)

    async def async_find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool],
    ) -> Optional[Bot]:
        c = self.bots.c
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                query = (
                    select(self.bots)
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
                exec = await session.execute(query)
                result = exec.first()
                if result:
                    return Bot(
                        app_id=result.app_id,
                        enterprise_id=result.enterprise_id,
                        team_id=result.team_id,
                        bot_token=result.bot_token,
                        bot_id=result.bot_id,
                        bot_user_id=result.bot_user_id,
                        bot_scopes=result.bot_scopes,
                        installed_at=result.installed_at,
                    )
                else:
                    return None

    # async def async_save(self, installation: Installation):
    #     async with Database(self.database_url) as database:
    #         async with database.transaction():
    #             i = installation.to_dict()
    #             i["client_id"] = self.client_id
    #             await database.execute(self.installations.insert(), i)
    #             b = installation.to_bot().to_dict()
    #             b["client_id"] = self.client_id
    #             await database.execute(self.bots.insert(), b)

    # async def async_find_bot(
    #     self,
    #     *,
    #     enterprise_id: Optional[str],
    #     team_id: Optional[str],
    #     is_enterprise_install: Optional[bool],
    # ) -> Optional[Bot]:
    #     c = self.bots.c
    #     query = (
    #         self.bots.select()
    #         .where(
    #             and_(
    #                 c.enterprise_id == enterprise_id,
    #                 c.team_id == team_id,
    #                 c.is_enterprise_install == is_enterprise_install,
    #             )
    #         )
    #         .order_by(desc(c.installed_at))
    #         .limit(1)
    #     )
    #     async with Database(self.database_url) as database:
    #         result = await database.fetch_one(query)
    #         if result:
    #             return Bot(
    #                 app_id=result["app_id"],
    #                 enterprise_id=result["enterprise_id"],
    #                 team_id=result["team_id"],
    #                 bot_token=result["bot_token"],
    #                 bot_id=result["bot_id"],
    #                 bot_user_id=result["bot_user_id"],
    #                 bot_scopes=result["bot_scopes"],
    #                 installed_at=result["installed_at"],
    #             )
    #         else:
    #             return None


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
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                stmt = self.oauth_states.insert().values(state=state, expire_at=now)
                await session.execute(stmt)
        return state

    async def async_consume(self, state: str) -> bool:
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                c = self.oauth_states.c
                query = select(self.oauth_states.c.id).where(
                    and_(c.state == state, c.expire_at > datetime.datetime.utcnow())
                )
                exec = await session.execute(query)
                row = exec.first()
                self.logger.debug(f"consume's query result: {row}")
                if row:
                    stmt = self.oauth_states.delete().where(c.id == row.id)
                    await session.execute(stmt)
                    return True
                return False
        return False

    # async def async_issue(self) -> str:
    #     state: str = str(uuid4())
    #     now = datetime.datetime.utcfromtimestamp(time.time() + self.expiration_seconds)
    #     async with Database(self.database_url) as database:
    #         await database.execute(
    #             self.oauth_states.insert(), {"state": state, "expire_at": now}
    #         )
    #         return state

    # async def async_consume(self, state: str) -> bool:
    #     try:
    #         async with Database(self.database_url) as database:
    #             async with database.transaction():
    #                 c = self.oauth_states.c
    #                 query = self.oauth_states.select().where(
    #                     and_(c.state == state, c.expire_at > datetime.datetime.utcnow())
    #                 )
    #                 row = await database.fetch_one(query)
    #                 self.logger.debug(f"consume's query result: {row}")
    #                 await database.execute(
    #                     self.oauth_states.delete().where(c.id == row["id"])
    #                 )
    #                 return True
    #         return False
    #     except Exception as e:
    #         message = f"Failed to find any persistent data for state: {state} - {e}"
    #         self.logger.warning(message)
    #         return False


def get_installation_store():
    return AsyncSQLAlchemyInstallationStore(
        client_id=config.get("_global_.secrets.slack.client_id"),
        database_url=globals.ASYNC_PG_CONN_STR,
        logger=logger,
    )


def get_slack_app():
    database_url = globals.ASYNC_PG_CONN_STR

    oauth_state_store = AsyncSQLAlchemyOAuthStateStore(
        expiration_seconds=120,
        database_url=database_url,
        logger=logger,
    )
    oauth_settings = AsyncOAuthSettings(
        client_id=config.get("_global_.secrets.slack.client_id"),
        client_secret=config.get("_global_.secrets.slack.client_secret"),
        state_store=oauth_state_store,
        installation_store=get_installation_store(),
        scopes=scopes,
        # user_scopes=scopes,
        install_path="/api/v3/slack/install",
        redirect_uri_path="/api/v3/slack/oauth_redirect",
    )

    slack_app = AsyncApp(
        logger=logger,
        installation_store=get_installation_store(),
        # token=config.get("_global_.secrets.slack.bot_token"),
        signing_secret=config.get("_global_.secrets.slack.signing_secret"),
        oauth_settings=oauth_settings,
        process_before_response=True,
    )

    @slack_app.command("/hello-noq")
    async def hello(body, ack):
        await ack(f"Hi <@{body['user_id']}>!")

    @slack_app.options("external_action")
    async def show_options(ack, respond, payload):
        await ack()
        keyword = payload.get("value")
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
        if keyword is not None and len(keyword) > 0:
            options = [o for o in options if keyword in o["text"]["text"]]
        if len(options) == 0:
            options = [
                {
                    "text": {"type": "plain_text", "text": "No Options"},
                    "value": "no-options",
                }
            ]
        await ack(options=options)

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

    @slack_app.middleware  # or app.use(log_request)
    async def log_request(logger, body, next):
        # logger.debug(body)
        return await next()

    return slack_app


# async def handle_select_resources_tenant(ack, body, client, logger, tenant):
#     await ack()


# async def handle_select_resources_options_tenant(ack, body, tenant):
#     """Handle the action of selecting resource options in a slack app dialog.

#     Arguments:
#         ack (func): Callback function to acknowledge the request.
#         body (dict): The request payload.
#         tenant (str): The tenant id.

#     Returns:
#         None: This function returns nothing.
#     """

#     slack_app_type = None
#     try:
#         private_metadata = json.loads(body["view"]["private_metadata"])
#         slack_app_type = private_metadata.get("app_type")
#     except (KeyError, json.JSONDecodeError):
#         private_metadata = {}
#         slack_app_type = body['action_id'].split("/")[-1]
#         if slack_app_type not in friendly_resource_type_names.keys():
#             slack_app_type = None


#     redis_key = config.get_tenant_specific_key(
#         "cache_organization_structure.redis.key.org_structure_key",
#         tenant,
#         f"{tenant}_IAMBIC_TEMPLATES",
#     )
#     template_dicts = await retrieve_json_data_from_redis_or_s3(
#         redis_key=redis_key,
#         tenant=tenant,
#     )
#     res = []
#     if slack_app_type:
#         res.extend(
#             jq.compile(
#                 f".[] | select(.template_type == \"{slack_app_type}\") | select(.identifier | test(\"{body['value']}\"; \"i\"))?"
#             )
#             .input(template_dicts)
#             .all()
#         )
#         res.extend(
#             jq.compile(
#                 f".[] | select(.template_type == \"{slack_app_type}\") | select(.properties.name | test(\"{body['value']}\"; \"i\"))?"
#             )
#             .input(template_dicts)
#             .all()
#         )

#     else:
#         res.extend(
#             jq.compile(f".[] | select(.identifier | test(\"{body['value']}\"; \"i\"))?")
#             .input(template_dicts)
#             .all()
#         )
#         res.extend(
#             jq.compile(
#                 f".[] | select(.properties.name | test(\"{body['value']}\"; \"i\"))?"
#             )
#             .input(template_dicts)
#             .all()
#         )
#     # Lambda to remove duplicates if repo_relative_file_path is the same
#     res = list({v["repo_relative_file_path"]: v for v in res}.values())

#     option_groups = defaultdict(list)
#     for typeahead_entry in res:
#         template_type = typeahead_entry["template_type"]
#         friendly_name = friendly_resource_type_names.get(template_type, template_type)
#         if not option_groups.get(friendly_name):
#             option_groups[friendly_name] = {
#                 "label": {"type": "plain_text", "text": friendly_name},
#                 "options": [],
#             }

#         option_groups[friendly_name]["options"].append(
#             {
#                 "text": {
#                     "type": "plain_text",
#                     "text": typeahead_entry.get(
#                         "identifier", typeahead_entry.get("properties", {}).get("name")
#                     ),
#                 },
#                 # Warning: Slack docs specify the max length of options value is 75 characters
#                 # but it is actually larger. Slack will not give you an error if this is exceeded,
#                 # and you will be left wandering aimlessly in the abyss.
#                 "value": typeahead_entry["hash"],
#             }
#         )
#     option_groups = [v for _, v in option_groups.items()]
#     option_groups_formatted = {
#         "option_groups": option_groups,
#     }
#     res = await ack(option_groups_formatted)


def create_log_request_handler(tenant):
    async def _log_request(logger, body, next):
        # logger.debug(body)
        return await next()

    return _log_request


# async def handle_request_access_to_resource_ack(ack):
#     await ack(response_action="update", view=request_access_to_resource_success)


# async def handle_request_cloud_permissions_to_resource_ack(ack):
#     await ack(response_action="update", view=select_desired_permissions_modal)


# async def handle_request_update_or_remove_tags_ack(ack):
#     await ack(response_action="update", view=update_or_remove_tags_modal)


# async def handle_select_cloud_identity_request_type(ack, body, client, logger, tenant):
#     await ack(
#         response_action="update",
#         view=self_service_request_permissions_step_2_option_selection,
#     )


# # @slack_app.view("request_access_to_resource")
# async def handle_request_access_to_resource_tenant(
#     body, client, logger, respond, tenant
# ):
#     tenant_config = TenantConfig(tenant)
#     reverse_hash_for_templates = await retrieve_json_data_from_redis_or_s3(
#         redis_key=tenant_config.iambic_templates_reverse_hash_redis_key,
#         tenant=tenant,
#     )

#     # TODO: Use original message
#     update=False
#     # original_message = await client.conversations_history(channel=body['container']['channel_id'], limit=1, latest=body['container']['message_ts'], inclusive=True)
#     # original_message_blocks = original_message._initial_data['messages'][0]['blocks']
#     # original_branch_name = None
#     # original_duration = None
#     # original_request_id = None
#     # original_user_email = None
#     # original_pull_request_id = None
#     # for block in original_message_blocks:
#     #     block_id = block.get('block_id')
#     #     if block_id.startswith('branch_name/'):
#     #         original_branch_name = block_id.replace('branch_name/', '')
#     #     if block_id.startswith('duration/'):
#     #         original_duration = block_id.replace('duration/', '')
#     #     if block_id.startswith('request_id/'):
#     #         original_request_id = block_id.replace('request_id/', '')
#     #     if block_id.startswith('user_email/'):
#     #         original_user_email = block_id.replace('user_email/', '')
#     #     if block_id.startswith('pull_request_id/'):
#     #         original_pull_request_id = block_id.replace('pull_request_id/', '')
#     # TODO: Use IambicGit to make a request
#     # TODO: Convert Slack username to e-mail
#     # justification = body["view"]["state"]["values"]["justification"]["justification"][
#     #     "value"
#     # ]
#     justification = body['state']['values']['justification']['justification']['value']
#     iambic = IambicGit(tenant)
#     iambic_repo = await get_iambic_repo(tenant)
#     username = body['user']['username']
#     user_info = await client.users_info(user=body["user"]["id"])
#     user_email = user_info._initial_data["user"]["profile"]["email"]
#     # selected_options = body["view"]["state"]["values"]["request_access"][
#     #     "select_resources"
#     # ]["selected_options"]
#     selected_options = []
#     resource_type = None
#     dynamic_select_options = body["state"]["values"]['select_resources']
#     for k, v in dynamic_select_options.items():
#         if k.startswith("select_resources/"):
#             resource_type = k.split('/')[1]
#             selected_options.extend(v['selected_options'])
#     # body['state']['values']['select_resources']['select_resources/NOQ::Okta::App']['selected_options']
#     duration = body["state"]["values"]["duration"]["duration"]["selected_option"]["value"]
#     template_changes = []
#     resources = defaultdict(list)
#     owners = []
#     # TODO: We need git url of resources
#     for option in selected_options:
#         hash = option["value"]
#         template = None
#         iambic_template_details = reverse_hash_for_templates[hash]
#         template_type = iambic_template_details["template_type"]
#         repo_name = iambic_template_details["repo_name"]
#         path = iambic_template_details["repo_relative_file_path"]
#         if template_type == "NOQ::Google::Group":
#             template = await iambic.google_add_user_to_group(
#                 template_type, repo_name, path, user_email, duration
#             )
#             resources[template_type].append(template.properties.name)

#         elif template_type == "NOQ::Okta::Group":
#             template = await iambic.okta_add_user_to_group(
#                 template_type, repo_name, path, user_email, duration
#             )
#             resources[template_type].append(template.properties.name)
#         elif template_type == "NOQ::Okta::App":
#             template = await iambic.okta_add_user_to_app(
#                 template_type, repo_name, path, user_email, duration
#             )
#             resources[template_type].append(template.properties.name)

#         if template and template.owner and "@" in template.owner:
#             try:
#                 # TODO: Message owners directly
#                 user_details = await client.users_lookupByEmail(email=template.owner)
#                 owners.append(user_details)
#             except SlackApiError:
#                 # Most likely a group e-mail address and not a user
#                 pass

#         # else:
#         #     raise Exception("Unsupported template type")
#         template_changes.append(
#             IambicTemplateChange(path=path, body=template.get_body(exclude_unset=False))
#         )
#     if not template_changes:
#         await respond(
#             response_action="errors",
#             errors={
#                 "select_resources": "You must select at least one resource to request access to"
#             },
#         )
#         return
#     # TODO: This request_id is WRONG
#     request_id = str(uuid4())
#     pull_request_id =  None
#     request_pr = GitHubPullRequest(
#         access_token=iambic_repo.access_token,
#         repo_name=iambic_repo.repo_name,
#         tenant=tenant,
#         request_id=request_id,
#         requested_by=user_email,
#         merge_on_approval=iambic_repo.merge_on_approval,
#         pull_request_id=pull_request_id,
#     )

#     request_notes = yaml.dump(
#         {
#             "justification": justification,
#             "slack_username": username,
#             "slack_email": user_email,
#             "selected_options": selected_options,
#             "duration": duration,
#             "resource_type": resource_type,
#         }
#     )
#     approvers = "engineering@noq.dev"
#     channel_id = "C045MFZ2A10"
#     db_tenant = await Tenant.get_by_name(tenant)
#     if not db_tenant:
#         raise Exception("Tenant not found")
#     if update:
#         # branch_name = original_branch_name
#         # TODO: Need more detailed description
#         await request_pr.update_request(
#             updated_by=user_email,
#             description="Updating change",
#             template_changes=template_changes,
#             request_notes=request_notes,
#             reset_branch=True
#         )
#     else:
#         res = await create_request(
#             db_tenant,
#             user_email,
#             justification,
#             template_changes,
#             request_method="SLACK",
#             slack_username=username,
#             slack_email=user_email,
#             duration=duration,
#             resource_type=resource_type,
#             request_notes=request_notes
#         )
#         full_request = res['request']
#         friendly_request = res['friendly_request']
#         # branch_name  = await request_pr.create_request(justification, template_changes, request_notes=request_notes)
#     pr_url = friendly_request["pull_request_url"]

#     slack_message_to_reviewers = self_service_permissions_review_blocks(
#         username, resources, duration, approvers, justification, pr_url, full_request.branch_name, full_request.id, user_email,
#     )
#     user_id = body["user"]["id"]
#     if update:
#         pass
#         # await client.chat_update(
#         #     channel=channel_id,
#         #     ts=original_message._initial_data['messages'][0]['ts'],
#         #     text="An access request is awaiting your review. (Updated)",
#         #     blocks=slack_message_to_reviewers,
#         # )
#     else:
#         await client.chat_postMessage(
#             channel=user_id,
#             text=(
#                 "Your request has been successfully submitted. "
#                 f"Click the link below to view more details: {pr_url}"
#             ),
#         )

#         await client.chat_postMessage(
#             channel=channel_id,
#             blocks=slack_message_to_reviewers,
#             text="An access request is awaiting your review.",
#         )

#         await respond(
#             replace_original=True,
#             blocks=get_self_service_submission_success_blocks(pr_url)
#         )


# async def handle_generic_ack(ack):
#     await ack()


# async def request_access_tenant(ack, body, client, tenant):
#     # Acknowledge the command request
#     await ack()
#     # Call views_open with the built-in client
#     await client.views_open(
#         # Pass a valid trigger_id within 3 seconds of receiving it
#         trigger_id=body["trigger_id"],
#         # View payload
#         view=request_access_to_resource_block,
#     )


# async def request_access_step_1_tenant(ack, body, client, tenant):
#     # Acknowledge the command request
#     await ack()
#     # Call views_open with the built-in client
#     # await client.views_open(
#     #     # Pass a valid trigger_id within 3 seconds of receiving it
#     #     trigger_id=body["trigger_id"],
#     #     # View payload
#     #     view=self_service_step_1_option_selection,
#     # )
#     await client.chat_postEphemeral(
#         # Pass the user ID of the person who invoked the command
#         user=body["user_id"],
#         # Pass the text of the message you want to send
#         text=" ",
#         blocks=self_service_step_1_blocks,
#         # Pass any additional parameters as necessary
#         # For example, you can specify the channel or thread to send the message in
#         channel=body["channel_id"],
#     )

# async def handle_self_service_select(ack, body, client, respond, tenant):
#     # Acknowledge the action to confirm receipt
#     await ack()
#     selected_option = body['state']['values']['self-service-select']['self-service-select']['selected_option']['value']
#     blocks = generate_self_service_step_2_app_group_access(
#         selected_option,
#         selected_options=None,
#         justification=None,
#         duration=None,
#         update=False,
#         )

#     await respond(
#         # Pass the user ID of the person who invoked the command
#         # user=body["user"]["id"],
#         # ts=body['container']['message_ts'],
#         # Pass the text of the message you want to send
#         replace_original=True,
#         text=" ",
#         blocks=blocks,
#         # Pass any additional parameters as necessary
#         # For example, you can specify the channel or thread to send the message in
#         # channel=body["channel"]["id"],
#     )
#     # TODO: add clears: The chat.update method can be used to update an existing
#     # message. You’ll need to pass the original message ts (it’s in the response
#     # payload when you send a message) so make sure to keep that for later.


# async def cancel_request(ack, body, client, respond, tenant):
#     await ack()
#     await respond(
#         replace_original=True,
#         delete_original=True,
#         text=" ",
#     )

# # async def create_request(ack, body, client, respond, tenant):
# #     await ack()

# #     await respond(
# #         replace_original=True,
# #         text="Your request has been successfully submitted.",
# #     )

# def render_step_2_request_access():
#     return {
#         "type": "modal",
#         "callback_id": "modal_step_2",
#         "title": {"type": "plain_text", "text": "Request Access"},
#         "blocks": [
#             {
#                 "type": "section",
#                 "text": {
#                     "type": "plain_text",
#                     "text": "Please fill out the form below to request access.",
#                 },
#             }
#         ],
#     }


# async def handle_select_app_type(ack, logger, body, client, respond, tenant):
#     # Acknowledge the action to confirm receipt
#     await ack()
#     view_template = request_access_to_resource_block
#     view_template["private_metadata"] = json.dumps(
#         {"app_type": body["actions"][0]["selected_option"]["value"]}
#     )
#     await client.views_update(
#         view_id=body["view"]["id"],
#         hash=body["view"]["hash"],
#         view=view_template,
#     )


# async def handle_select_cloud_identities_options_tenant(
#     ack, logger, body, client, respond, tenant
# ):
#     tenant_config = TenantConfig(tenant)
#     res = await retrieve_json_data_from_redis_or_s3(
#         redis_key=tenant_config.iambic_arn_typeahead_redis_key, tenant=tenant
#     )

#     # reverse_hash_for_arn = await retrieve_json_data_from_redis_or_s3(
#     #             redis_key=tenant_config.iambic_hash_arn_redis_key,
#     #             tenant=tenant,
#     #         )
#     num_entries = 0
#     option_groups = defaultdict(list)
#     for typeahead_entry, template_details in res.items():

#         # Maximum length of option group options is 100:
#         if num_entries >= 100:
#             break
#         reverse_hash_for_arn = template_details["hash"]
#         account_id = typeahead_entry.split(":")[4]
#         account_name = template_details["account_name"]
#         partial_arn = typeahead_entry.replace(f"arn:aws:iam::{account_id}:", "")
#         account_name_arn = partial_arn.replace(
#             partial_arn, f"{account_name}:{partial_arn}"
#         )
#         if not (
#             body["value"].lower() in typeahead_entry.lower()
#             or body["value"].lower() in account_name_arn.lower()
#         ):
#             continue
#         template_type = template_details["template_type"]

#         friendly_name = friendly_resource_type_names.get(template_type, template_type)
#         if not option_groups.get(friendly_name):
#             option_groups[friendly_name] = {
#                 "label": {"type": "plain_text", "text": friendly_name[:75]},
#                 "options": [],
#             }

#         option_groups[friendly_name]["options"].append(
#             {
#                 "text": {
#                     "type": "plain_text",
#                     "text": account_name_arn[:75],
#                 },
#                 # Warning: Slack docs specify the max length of options value is 75 characters
#                 # but it is actually larger. Slack will not give you an error if this is exceeded,
#                 # and you will be left wandering aimlessly in the abyss.
#                 "value": reverse_hash_for_arn[:75],
#             }
#         )
#         num_entries += 1
#     option_groups = [v for _, v in option_groups.items()]
#     option_groups_formatted = {
#         "option_groups": option_groups,
#     }
#     res = await ack(option_groups_formatted)


# async def handle_request_access_step_1_callback(
#     ack, logger, body, client, respond, tenant
# ):
#     # Acknowledge the action to confirm receipt
#     await ack()

#     # Get the value of the selected radio button
#     selected_option = body["view"]["state"]["values"]["self_service_step_1_block"][
#         "self_service_step_1_option_selection"
#     ]["selected_option"]["value"]

#     # Render step 2 conditionally based on the selected option
#     if selected_option == "request_access_to_identity":
#         view = request_access_to_resource_block
#     elif selected_option == "request_permissions_for_identity":
#         view = self_service_request_permissions_step_2_option_selection
#     else:
#         raise Exception("Invalid option selected")
#     await ack(response_action="update", view=view)


# async def handle_user_change_events(body, logger, tenant):
#     pass


# async def handle_select_aws_actions_options(ack, logger, body, client, respond, tenant):
#     # Acknowledge the action to confirm receipt
#     await ack()
#     # Get the value of the selected radio button
#     options = []
#     prefix = body["value"] + "*"
#     results = sorted(_expand_wildcard_action(prefix))
#     services = sorted(list({r.split(":")[0].replace("*", "") for r in results}))
#     if body["value"].endswith("*"):
#         options.append(
#             {
#                 "text": {
#                     "type": "plain_text",
#                     "text": body["value"][:75],
#                 },
#                 "value": body["value"][:75],
#             }
#         )
#     for service in services:
#         options.append(
#             {
#                 "text": {
#                     "type": "plain_text",
#                     "text": f"{service[:75]}",
#                 },
#                 "value": f"{service[:75]}",
#             }
#         )
#     # for result in results:
#     #     options.append(
#     #         {
#     #             "text": {
#     #                 "type": "plain_text",
#     #                 "text": result[:75],
#     #             },
#     #             "value": result[:75],
#     #         }
#     #     )
#     await ack(options=options[:100])

# async def handle_edit_request(ack, client, body, logger, respond, tenant):
#     # Acknowledge the action to confirm receipt
#     await ack()
#     # print edit screen. Prefill?
#     # TODO: git fetch origin 'refs/notes/*':'refs/notes/*'
#     # git log --show-notes='*'
#     iambic = IambicGit(tenant)
#     iambic_repo = await get_iambic_repo(tenant)
#     branch_name = None
#     pull_request_id = None
#     user_email = None
#     request_id = None
#     for block in body['message']['blocks']:
#         block_id = block.get('block_id', "")
#         if block_id.startswith("pull_request_id/"):
#             pull_request_id = block_id.replace("pull_request_id/", "")
#         elif block_id.startswith("user_email/"):
#             user_email = block_id.replace("user_email/", "")
#         elif block_id.startswith("request_id/"):
#             request_id = block_id.replace("request_id/", "")
#         elif block_id.startswith("branch_name/"):
#             branch_name = block_id.replace("branch_name/", "")
#     request_pr = await get_iambic_pr_instance(
#         tenant, request_id, user_email, pull_request_id
#     )
#     request_details = await request_pr.get_request_details()

#     try:
#         request_notes_s = await request_pr.get_request_notes(branch_name)
#         request_notes = yaml.load(request_notes_s)
#         selectied_options = json.loads(json.dumps(request_notes))["selected_options"]
#         resource_type = request_notes["resource_type"]
#         blocks = generate_self_service_step_2_app_group_access(
#             resource_type,
#             selected_options=selectied_options,
#             justification=request_notes["justification"],
#             duration=request_notes["duration"],
#             update=True,
#             message_ts=body['message']['ts'],
#             channel_id=body['channel']['id'],
#             branch_name=branch_name,
#             pull_request_id=pull_request_id,
#             user_email=user_email,
#             request_id=request_id

#         )
#         await client.chat_postEphemeral(
#             user=body["user"]["id"],
#             text=" ",
#             blocks=blocks,
#             channel=body["channel"]["id"],
#         )
#     except Exception as e:
#         log.error(f"Error getting request notes: {e}")

#     # request_pr.update_request()


# async def handle_request_permissions_step_2_option_selection(ack, body, logger, tenant):
#     # Acknowledge the action to confirm receipt
#     await ack()

#     # Get the value of the selected radio button
#     selected_option = body["view"]["state"]["values"][
#         "self_service_permissions_step_2_block"
#     ]["self_service_step_2_option_selection"]["selected_option"]["value"]

#     # Render step 2 conditionally based on the selected option
#     if selected_option == "select_predefined_policy":
#         view = ""
#     elif selected_option == "update_inline_policies":
#         view = select_desired_permissions_modal
#     elif selected_option == "update_managed_policies":
#         view = ""
#     elif selected_option == "update_tags":
#         view = update_or_remove_tags_modal
#     else:
#         raise Exception("Invalid option selected")
#     await ack(response_action="update", view=view)


# async def select_aws_services_action(ack, body, logger, client, tenant):
#     await ack()
#     view_template = select_desired_permissions_modal
#     view_template["private_metadata"] = json.dumps(
#         {
#             "actions": [
#                 b["value"]
#                 for b in body["view"]["state"]["values"]["select_services"][
#                     "select_aws_services_action"
#                 ]["selected_options"]
#             ]
#         }
#     )
#     await client.views_update(
#         view_id=body["view"]["id"],
#         hash=body["view"]["hash"],
#         view=view_template,
#     )
#     logger.info(body)


# async def handle_select_aws_resources_options(
#     ack, logger, body, client, respond, tenant
# ):
#     # Acknowledge the action to confirm receipt
#     await ack()
#     # Get the value of the selected radio button
#     options = []
#     prefix = body["value"] + "*"
#     try:
#         private_metadata = json.loads(body["view"]["private_metadata"])
#     except (KeyError, json.JSONDecodeError):
#         private_metadata = {}
#     resource_redis_cache_key = config.get_tenant_specific_key(
#         "aws_config_cache.redis_key",
#         tenant,
#         f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
#     )
#     red = await RedisHandler().redis(tenant)
#     all_resource_arns = await aio_wrapper(red.hkeys, resource_redis_cache_key)

#     for resource in all_resource_arns:
#         if len(options) >= 100:
#             break
#         if body["value"] not in resource:
#             continue
#         action_included = False
#         # If user selected AWS actions, make sure the resources we're looking up
#         # are compatible with the actions
#         if private_metadata.get("actions"):
#             for full_action in private_metadata["actions"]:
#                 if full_action == "*":
#                     action_included = True
#                     break
#                 expected_prefix = f"arn:aws:{full_action.split(':')[0]}"
#                 if not resource.startswith(expected_prefix):
#                     continue
#                 action_included = True
#                 break
#         else:
#             action_included = True
#         if not action_included:
#             continue
#         options.append(
#             {
#                 "text": {
#                     "type": "plain_text",
#                     "text": resource[:75],
#                 },
#                 "value": resource[:75],
#             }
#         )
#     await ack(options=options)


# async def handle_request_update_or_remove_tags(logger, body, client, respond, tenant):
#     tenant_config = TenantConfig(tenant)
#     reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
#         redis_key=tenant_config.iambic_hash_arn_redis_key,
#         tenant=tenant,
#     )

#     justification = body["view"]["state"]["values"]["justification"]["justification"][
#         "value"
#     ]

#     selected_identities = body["view"]["state"]["values"]["select_identities"][
#         "select_identities_action"
#     ]["selected_options"]


# async def handle_request_cloud_permissions_to_resources(
#     body,
#     client,
#     logger,
#     respond,
#     tenant,
# ):
#     tenant_config = TenantConfig(tenant)
#     # res = await retrieve_json_data_from_redis_or_s3(
#     #     redis_key=tenant_config.iambic_arn_typeahead_redis_key,
#     #     tenant=tenant
#     # )
#     iambic_aws_accounts = await retrieve_json_data_from_redis_or_s3(
#         redis_key=tenant_config.iambic_aws_accounts,
#         tenant=tenant,
#     )
#     # TODO: Get account names affected by user change
#     reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
#         redis_key=tenant_config.iambic_hash_arn_redis_key,
#         tenant=tenant,
#     )
#     justification = body["view"]["state"]["values"]["justification"]["justification"][
#         "value"
#     ]
#     iambic = IambicGit(tenant)
#     iambic_repo = await get_iambic_repo(tenant)
#     username = body['user']['username']
#     user_info = await client.users_info(user=body["user"]["id"])
#     user_email = user_info._initial_data["user"]["profile"]["email"]
#     selected_identities = body["view"]["state"]["values"]["select_identities"][
#         "select_identities_action"
#     ]["selected_options"]
#     selected_actions = [
#         b["value"]
#         for b in body["view"]["state"]["values"]["select_services"][
#             "select_aws_services_action"
#         ]["selected_options"]
#     ]
#     selected_resources = [
#         b["value"]
#         for b in body["view"]["state"]["values"]["select_resources"][
#             "select_aws_resources_action"
#         ]["selected_options"]
#     ]
#     selected_permissions = [
#         b["value"]
#         for b in body["view"]["state"]["values"]["desired_permissions"][
#             "desired_permissions_action"
#         ]["selected_options"]
#     ]

#     all_aws_actions = []
#     services = []
#     for action in selected_actions:
#         service = action.split(":")[0]
#         if service == "*":
#             aws_actions = ["*"]
#         else:
#             aws_actions = await _get_policy_sentry_access_level_actions(
#                 service, selected_permissions
#             )
#         all_aws_actions.extend(aws_actions)
#     duration = body["view"]["state"]["values"]["duration"]["duration"][
#         "selected_option"
#     ]["value"]

#     template_changes = {}
#     resources = defaultdict(list)
#     for identity in selected_identities:
#         identity_hash = identity["value"]
#         template = template_changes.get(identity_hash, None)
#         if template:
#             template = template.template
#         identity_info = reverse_hash_for_arns[identity_hash]
#         arn = identity_info["arn"]
#         account_id = arn.split(":")[4]
#         account_name = account_id
#         for account in iambic_aws_accounts:
#             if account["account_id"] == account_id:
#                 account_name = account["account_name"]
#                 break
#         template_type = identity_info["template_type"]
#         repo_name = identity_info["repo_name"]
#         repo_relative_file_path = identity_info["repo_relative_file_path"]
#         file_path = identity_info["file_path"]
#         if template_type == "NOQ::AWS::IAM::Role":
#             template = await iambic.aws_iam_role_add_inline_policy(
#                 template_type,
#                 repo_name,
#                 repo_relative_file_path,
#                 user_email,
#                 duration,
#                 all_aws_actions,
#                 selected_resources,
#                 account_name,
#                 existing_template=template
#                 # TODO: If I modify 2 roles on the same account, we need
#                 # to recurse over the template to make sure both sets of changes
#                 # are captured in a single template
#             )
#             resources[template_type].append(template.identifier)
#             print(template)
#             # if template.owner:
#             #     user_info = await client.users_lookupByEmail(email=email)
#             #     owners[template.owner] = user_info
#         template_changes[identity_hash] = IambicTemplateChange(
#             path=repo_relative_file_path,
#             body=template.get_body(exclude_unset=False),
#             template=template,
#         )
#     if not template_changes:
#         await respond(
#             response_action="errors",
#             errors={
#                 "select_resources": "You must select at least one resource to request access to"
#             },
#         )
#         return

#     request_id = str(uuid4())
#     pull_request_id = None
#     request_pr = GitHubPullRequest(
#         access_token=iambic_repo.access_token,
#         repo_name=iambic_repo.repo_name,
#         tenant=tenant,
#         request_id=request_id,
#         requested_by=user_email,
#         merge_on_approval=iambic_repo.merge_on_approval,
#         pull_request_id=pull_request_id,
#     )

#     branch_name = await request_pr.create_request(justification, template_changes.values())
#     request_details = await request_pr.get_request_details()
#     pr_url = request_details["pull_request_url"]
#     reviewers = "engineering@noq.dev"
#     channel_id = "C045MFZ2A10"
#     slack_message_to_reviewers = self_service_permissions_review_blocks(
#         username, resources, duration, reviewers, justification, pr_url, branch_name, request_id, user_email,
#     )

#     user_id = body["user"]["id"]

#     await client.chat_postMessage(
#         channel=user_id,
#         text=(
#             "Your request has been successfully submitted. "
#             f"Click the link below to view more details: {pr_url}"
#         ),
#     )
#     # TODO: Grab maessage sent to this channel and post as a comment on PR
#     await client.chat_postMessage(
#         channel=channel_id,
#         blocks=slack_message_to_reviewers,
#         text="An access request is awaiting your review.",
#     )

#     view_id = body["view"]["id"]
#     # Update view
#     await client.views_update(
#         view_id=view_id,
#         view=self_service_submission_success.replace(
#             "{{pull_request_url}}", pr_url
#         ),  # TODO change
#     )


class TenantAsyncSlackApp(AsyncApp):
    pass


class TenantSlackApp:
    def __init__(self, tenant, enterprise_id, team_id, app_id):
        self.tenant = tenant
        self.enterprise_id = enterprise_id
        self.team_id = team_id
        self.app_id = app_id
        self.tenant_slack_app = None

    async def handle_generic_ack(self, ack):
        await ack()

    async def noq_command_welcome_selection(self, ack, body, client):
        await ack()
        await client.chat_postEphemeral(
            user=body["user_id"],
            text=" ",
            blocks=self_service_step_1_blocks,
            channel=body["channel_id"],
        )

    async def handle_select_resources_options_tenant(self, ack, body):
        """Handle the action of selecting resource options in a slack app dialog.

        Arguments:
            ack (func): Callback function to acknowledge the request.
            body (dict): The request payload.
            tenant (str): The tenant id.

        Returns:
            None: This function returns nothing.
        """

        slack_app_type = None
        try:
            private_metadata = json.loads(body["view"]["private_metadata"])
            slack_app_type = private_metadata.get("app_type")
        except (KeyError, json.JSONDecodeError):
            private_metadata = {}
            slack_app_type = body["action_id"].split("/")[-1]
            if slack_app_type not in friendly_resource_type_names.keys():
                slack_app_type = None

        redis_key = config.get_tenant_specific_key(
            "cache_organization_structure.redis.key.org_structure_key",
            self.tenant,
            f"{self.tenant}_IAMBIC_TEMPLATES",
        )
        template_dicts = await retrieve_json_data_from_redis_or_s3(
            redis_key=redis_key,
            tenant=self.tenant,
        )
        res = []
        if slack_app_type:
            res.extend(
                jq.compile(
                    f".[] | select(.template_type == \"{slack_app_type}\") | select(.identifier | test(\"{body['value']}\"; \"i\"))?"
                )
                .input(template_dicts)
                .all()
            )
            res.extend(
                jq.compile(
                    f".[] | select(.template_type == \"{slack_app_type}\") | select(.properties.name | test(\"{body['value']}\"; \"i\"))?"
                )
                .input(template_dicts)
                .all()
            )

        else:
            res.extend(
                jq.compile(
                    f".[] | select(.identifier | test(\"{body['value']}\"; \"i\"))?"
                )
                .input(template_dicts)
                .all()
            )
            res.extend(
                jq.compile(
                    f".[] | select(.properties.name | test(\"{body['value']}\"; \"i\"))?"
                )
                .input(template_dicts)
                .all()
            )
        # Lambda to remove duplicates if repo_relative_file_path is the same
        res = list({v["repo_relative_file_path"]: v for v in res}.values())

        option_groups = defaultdict(list)
        for typeahead_entry in res:
            template_type = typeahead_entry["template_type"]
            friendly_name = friendly_resource_type_names.get(
                template_type, template_type
            )
            if not option_groups.get(friendly_name):
                option_groups[friendly_name] = {
                    "label": {"type": "plain_text", "text": friendly_name},
                    "options": [],
                }

            option_groups[friendly_name]["options"].append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": typeahead_entry.get(
                            "identifier",
                            typeahead_entry.get("properties", {}).get("name"),
                        ),
                    },
                    # Warning: Slack docs specify the max length of options value is 75 characters
                    # but it is actually larger. Slack will not give you an error if this is exceeded,
                    # and you will be left wandering aimlessly in the abyss.
                    "value": typeahead_entry["hash"],
                }
            )
        option_groups = [v for _, v in option_groups.items()]
        option_groups_formatted = {
            "option_groups": option_groups,
        }
        res = await ack(option_groups_formatted)

    async def handle_self_service_select(self, ack, body, client, respond):
        # Acknowledge the action to confirm receipt
        await ack()
        selected_option = body["state"]["values"]["self-service-select"][
            "self-service-select"
        ]["selected_option"]["value"]
        blocks = generate_self_service_step_2_app_group_access(
            selected_option,
            selected_options=None,
            justification=None,
            duration=None,
            update=False,
        )

        await respond(
            # Pass the user ID of the person who invoked the command
            # user=body["user"]["id"],
            # ts=body['container']['message_ts'],
            # Pass the text of the message you want to send
            replace_original=True,
            text=" ",
            blocks=blocks,
            # Pass any additional parameters as necessary
            # For example, you can specify the channel or thread to send the message in
            # channel=body["channel"]["id"],
        )
        # TODO: add clears: The chat.update method can be used to update an existing
        # message. You’ll need to pass the original message ts (it’s in the response
        # payload when you send a message) so make sure to keep that for later.

    async def cancel_request(self, ack, body, client, respond):
        await ack()
        await respond(
            replace_original=True,
            delete_original=True,
            text=" ",
        )

    async def handle_request_access_to_resource_ack(self, ack):
        await ack(response_action="update", view=request_access_to_resource_success)

    async def handle_request_access_step_1_callback(
        self, ack, logger, body, client, respond
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
            view = self_service_request_permissions_step_2_option_selection
        else:
            raise Exception("Invalid option selected")
        await ack(response_action="update", view=view)

    async def handle_request_access_to_resource_tenant(
        self, body, client, logger, respond
    ):
        tenant_config = TenantConfig(self.tenant)
        reverse_hash_for_templates = await retrieve_json_data_from_redis_or_s3(
            redis_key=tenant_config.iambic_templates_reverse_hash_redis_key,
            tenant=self.tenant,
        )

        # TODO: Use original message
        update = False
        # original_message = await client.conversations_history(channel=body['container']['channel_id'], limit=1, latest=body['container']['message_ts'], inclusive=True)
        # original_message_blocks = original_message._initial_data['messages'][0]['blocks']
        # original_branch_name = None
        # original_duration = None
        # original_request_id = None
        # original_user_email = None
        # original_pull_request_id = None
        # for block in original_message_blocks:
        #     block_id = block.get('block_id')
        #     if block_id.startswith('branch_name/'):
        #         original_branch_name = block_id.replace('branch_name/', '')
        #     if block_id.startswith('duration/'):
        #         original_duration = block_id.replace('duration/', '')
        #     if block_id.startswith('request_id/'):
        #         original_request_id = block_id.replace('request_id/', '')
        #     if block_id.startswith('user_email/'):
        #         original_user_email = block_id.replace('user_email/', '')
        #     if block_id.startswith('pull_request_id/'):
        #         original_pull_request_id = block_id.replace('pull_request_id/', '')
        # TODO: Use IambicGit to make a request
        # TODO: Convert Slack username to e-mail
        # justification = body["view"]["state"]["values"]["justification"]["justification"][
        #     "value"
        # ]
        justification = body["state"]["values"]["justification"]["justification"][
            "value"
        ]
        iambic = IambicGit(self.tenant)
        iambic_repo = await get_iambic_repo(self.tenant)
        username = body["user"]["username"]
        user_info = await client.users_info(user=body["user"]["id"])
        user_email = user_info._initial_data["user"]["profile"]["email"]
        # selected_options = body["view"]["state"]["values"]["request_access"][
        #     "select_resources"
        # ]["selected_options"]
        selected_options = []
        resource_type = None
        dynamic_select_options = body["state"]["values"]["select_resources"]
        for k, v in dynamic_select_options.items():
            if k.startswith("select_resources/"):
                resource_type = k.split("/")[1]
                selected_options.extend(v["selected_options"])
        # body['state']['values']['select_resources']['select_resources/NOQ::Okta::App']['selected_options']
        duration = body["state"]["values"]["duration"]["duration"]["selected_option"][
            "value"
        ]
        template_changes = []
        resources = defaultdict(list)
        owners = []
        # TODO: We need git url of resources
        for option in selected_options:
            hash = option["value"]
            template = None
            iambic_template_details = reverse_hash_for_templates[hash]
            template_type = iambic_template_details["template_type"]
            repo_name = iambic_template_details["repo_name"]
            path = iambic_template_details["repo_relative_file_path"]
            if template_type == "NOQ::Google::Group":
                template = await iambic.google_add_user_to_group(
                    template_type, repo_name, path, user_email, duration
                )
                resources[template_type].append(template.properties.name)

            elif template_type == "NOQ::Okta::Group":
                template = await iambic.okta_add_user_to_group(
                    template_type, repo_name, path, user_email, duration
                )
                resources[template_type].append(template.properties.name)
            elif template_type == "NOQ::Okta::App":
                template = await iambic.okta_add_user_to_app(
                    template_type, repo_name, path, user_email, duration
                )
                resources[template_type].append(template.properties.name)

            if template and template.owner and "@" in template.owner:
                try:
                    # TODO: Message owners directly
                    user_details = await client.users_lookupByEmail(
                        email=template.owner
                    )
                    owners.append(user_details)
                except SlackApiError:
                    # Most likely a group e-mail address and not a user
                    pass

            # else:
            #     raise Exception("Unsupported template type")
            template_changes.append(
                IambicTemplateChange(
                    path=path, body=template.get_body(exclude_unset=False)
                )
            )
        if not template_changes:
            await respond(
                response_action="errors",
                errors={
                    "select_resources": "You must select at least one resource to request access to"
                },
            )
            return
        # TODO: This request_id is WRONG
        request_id = str(uuid4())
        pull_request_id = None
        request_pr = GitHubPullRequest(
            access_token=iambic_repo.access_token,
            repo_name=iambic_repo.repo_name,
            tenant=self.tenant,
            request_id=request_id,
            requested_by=user_email,
            merge_on_approval=iambic_repo.merge_on_approval,
            pull_request_id=pull_request_id,
        )

        request_notes = yaml.dump(
            {
                "justification": justification,
                "slack_username": username,
                "slack_email": user_email,
                "selected_options": selected_options,
                "duration": duration,
                "resource_type": resource_type,
            }
        )
        approvers = "engineering@noq.dev"
        channel_id = "C045MFZ2A10"
        db_tenant = await Tenant.get_by_name(self.tenant)
        if not db_tenant:
            raise Exception("Tenant not found")
        if update:
            # branch_name = original_branch_name
            # TODO: Need more detailed description
            await request_pr.update_request(
                updated_by=user_email,
                description="Updating change",
                template_changes=template_changes,
                request_notes=request_notes,
                reset_branch=True,
            )
        else:
            res = await create_request(
                db_tenant,
                user_email,
                justification,
                template_changes,
                request_method="SLACK",
                slack_username=username,
                slack_email=user_email,
                duration=duration,
                resource_type=resource_type,
                request_notes=request_notes,
            )
            full_request = res["request"]
            friendly_request = res["friendly_request"]
            # branch_name  = await request_pr.create_request(justification, template_changes, request_notes=request_notes)
        pr_url = friendly_request["pull_request_url"]

        slack_message_to_reviewers = self_service_permissions_review_blocks(
            username,
            resources,
            duration,
            approvers,
            justification,
            pr_url,
            full_request.branch_name,
            full_request.id,
            user_email,
        )
        user_id = body["user"]["id"]
        if update:
            pass
            # await client.chat_update(
            #     channel=channel_id,
            #     ts=original_message._initial_data['messages'][0]['ts'],
            #     text="An access request is awaiting your review. (Updated)",
            #     blocks=slack_message_to_reviewers,
            # )
        else:
            await client.chat_postMessage(
                channel=user_id,
                text=(
                    "Your request has been successfully submitted. "
                    f"Click the link below to view more details: {pr_url}"
                ),
            )

            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_message_to_reviewers,
                text="An access request is awaiting your review.",
            )

            await respond(
                replace_original=True,
                blocks=get_self_service_submission_success_blocks(pr_url),
            )

    async def handle_select_app_type(self, ack, logger, body, client, respond):
        # Acknowledge the action to confirm receipt
        await ack()
        view_template = request_access_to_resource_block
        view_template["private_metadata"] = json.dumps(
            {"app_type": body["actions"][0]["selected_option"]["value"]}
        )
        await client.views_update(
            view_id=body["view"]["id"],
            hash=body["view"]["hash"],
            view=view_template,
        )

    async def handle_edit_request(self, ack, client, body, logger, respond):
        # Acknowledge the action to confirm receipt
        await ack()
        # print edit screen. Prefill?
        # TODO: git fetch origin 'refs/notes/*':'refs/notes/*'
        # git log --show-notes='*'
        iambic = IambicGit(self.tenant)
        iambic_repo = await get_iambic_repo(self.tenant)
        branch_name = None
        pull_request_id = None
        user_email = None
        request_id = None
        for block in body["message"]["blocks"]:
            block_id = block.get("block_id", "")
            if block_id.startswith("pull_request_id/"):
                pull_request_id = block_id.replace("pull_request_id/", "")
            elif block_id.startswith("user_email/"):
                user_email = block_id.replace("user_email/", "")
            elif block_id.startswith("request_id/"):
                request_id = block_id.replace("request_id/", "")
            elif block_id.startswith("branch_name/"):
                branch_name = block_id.replace("branch_name/", "")
        request_pr = await get_iambic_pr_instance(
            self.tenant, request_id, user_email, pull_request_id
        )
        request_details = await request_pr.get_request_details()

        try:
            request_notes_s = await request_pr.get_request_notes(branch_name)
            request_notes = yaml.load(request_notes_s)
            selectied_options = json.loads(json.dumps(request_notes))[
                "selected_options"
            ]
            resource_type = request_notes["resource_type"]
            blocks = generate_self_service_step_2_app_group_access(
                resource_type,
                selected_options=selectied_options,
                justification=request_notes["justification"],
                duration=request_notes["duration"],
                update=True,
                message_ts=body["message"]["ts"],
                channel_id=body["channel"]["id"],
                branch_name=branch_name,
                pull_request_id=pull_request_id,
                user_email=user_email,
                request_id=request_id,
            )
            await client.chat_postEphemeral(
                user=body["user"]["id"],
                text=" ",
                blocks=blocks,
                channel=body["channel"]["id"],
            )
        except Exception as e:
            log.error(f"Error getting request notes: {e}")

    async def handle_request_permissions_step_2_option_selection(
        self, ack, body, logger
    ):
        # Acknowledge the action to confirm receipt
        await ack()

        # Get the value of the selected radio button
        selected_option = body["view"]["state"]["values"][
            "self_service_permissions_step_2_block"
        ]["self_service_step_2_option_selection"]["selected_option"]["value"]

        # Render step 2 conditionally based on the selected option
        if selected_option == "select_predefined_policy":
            view = ""
        elif selected_option == "update_inline_policies":
            view = select_desired_permissions_modal
        elif selected_option == "update_managed_policies":
            view = ""
        elif selected_option == "update_tags":
            view = update_or_remove_tags_modal
        else:
            raise Exception("Invalid option selected")
        await ack(response_action="update", view=view)

    async def handle_select_cloud_identities_options_tenant(
        self, ack, logger, body, client, respond
    ):
        tenant_config = TenantConfig(self.tenant)
        res = await retrieve_json_data_from_redis_or_s3(
            redis_key=tenant_config.iambic_arn_typeahead_redis_key, tenant=self.tenant
        )

        # reverse_hash_for_arn = await retrieve_json_data_from_redis_or_s3(
        #             redis_key=tenant_config.iambic_hash_arn_redis_key,
        #             tenant=tenant,
        #         )
        num_entries = 0
        option_groups = defaultdict(list)
        for typeahead_entry, template_details in res.items():

            # Maximum length of option group options is 100:
            if num_entries >= 100:
                break
            reverse_hash_for_arn = template_details["hash"]
            account_id = typeahead_entry.split(":")[4]
            account_name = template_details["account_name"]
            partial_arn = typeahead_entry.replace(f"arn:aws:iam::{account_id}:", "")
            account_name_arn = partial_arn.replace(
                partial_arn, f"{account_name}:{partial_arn}"
            )
            if not (
                body["value"].lower() in typeahead_entry.lower()
                or body["value"].lower() in account_name_arn.lower()
            ):
                continue
            template_type = template_details["template_type"]

            friendly_name = friendly_resource_type_names.get(
                template_type, template_type
            )
            if not option_groups.get(friendly_name):
                option_groups[friendly_name] = {
                    "label": {"type": "plain_text", "text": friendly_name[:75]},
                    "options": [],
                }

            option_groups[friendly_name]["options"].append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": account_name_arn[:75],
                    },
                    # Warning: Slack docs specify the max length of options value is 75 characters
                    # but it is actually larger. Slack will not give you an error if this is exceeded,
                    # and you will be left wandering aimlessly in the abyss.
                    "value": reverse_hash_for_arn[:75],
                }
            )
            num_entries += 1
        option_groups = [v for _, v in option_groups.items()]
        option_groups_formatted = {
            "option_groups": option_groups,
        }
        res = await ack(option_groups_formatted)

    async def handle_select_aws_actions_options(
        self, ack, logger, body, client, respond
    ):
        # Acknowledge the action to confirm receipt
        await ack()
        # Get the value of the selected radio button
        options = []
        prefix = body["value"] + "*"
        results = sorted(_expand_wildcard_action(prefix))
        services = sorted(list({r.split(":")[0].replace("*", "") for r in results}))
        if body["value"].endswith("*"):
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": body["value"][:75],
                    },
                    "value": body["value"][:75],
                }
            )
        for service in services:
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": f"{service[:75]}",
                    },
                    "value": f"{service[:75]}",
                }
            )
        # for result in results:
        #     options.append(
        #         {
        #             "text": {
        #                 "type": "plain_text",
        #                 "text": result[:75],
        #             },
        #             "value": result[:75],
        #         }
        #     )
        await ack(options=options[:100])

    async def handle_select_aws_resources_options(
        self, ack, logger, body, client, respond
    ):
        # Acknowledge the action to confirm receipt
        await ack()
        # Get the value of the selected radio button
        options = []
        prefix = body["value"] + "*"
        try:
            private_metadata = json.loads(body["view"]["private_metadata"])
        except (KeyError, json.JSONDecodeError):
            private_metadata = {}
        resource_redis_cache_key = config.get_tenant_specific_key(
            "aws_config_cache.redis_key",
            self.tenant,
            f"{self.tenant}_AWSCONFIG_RESOURCE_CACHE",
        )
        red = await RedisHandler().redis(self.tenant)
        all_resource_arns = await aio_wrapper(red.hkeys, resource_redis_cache_key)

        for resource in all_resource_arns:
            if len(options) >= 100:
                break
            if body["value"] not in resource:
                continue
            action_included = False
            # If user selected AWS actions, make sure the resources we're looking up
            # are compatible with the actions
            if private_metadata.get("actions"):
                for full_action in private_metadata["actions"]:
                    if full_action == "*":
                        action_included = True
                        break
                    expected_prefix = f"arn:aws:{full_action.split(':')[0]}"
                    if not resource.startswith(expected_prefix):
                        continue
                    action_included = True
                    break
            else:
                action_included = True
            if not action_included:
                continue
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": resource[:75],
                    },
                    "value": resource[:75],
                }
            )
        await ack(options=options)

    async def handle_request_cloud_permissions_to_resources(
        self,
        body,
        client,
        logger,
        respond,
    ):
        tenant_config = TenantConfig(self.tenant)
        # res = await retrieve_json_data_from_redis_or_s3(
        #     redis_key=tenant_config.iambic_arn_typeahead_redis_key,
        #     tenant=tenant
        # )
        iambic_aws_accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key=tenant_config.iambic_aws_accounts,
            tenant=self.tenant,
        )
        # TODO: Get account names affected by user change
        reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
            redis_key=tenant_config.iambic_hash_arn_redis_key,
            tenant=self.tenant,
        )
        justification = body["view"]["state"]["values"]["justification"][
            "justification"
        ]["value"]
        iambic = IambicGit(self.tenant)
        iambic_repo = await get_iambic_repo(self.tenant)
        username = body["user"]["username"]
        user_info = await client.users_info(user=body["user"]["id"])
        user_email = user_info._initial_data["user"]["profile"]["email"]
        selected_identities = body["view"]["state"]["values"]["select_identities"][
            "select_identities_action"
        ]["selected_options"]
        selected_actions = [
            b["value"]
            for b in body["view"]["state"]["values"]["select_services"][
                "select_aws_services_action"
            ]["selected_options"]
        ]
        selected_resources = [
            b["value"]
            for b in body["view"]["state"]["values"]["select_resources"][
                "select_aws_resources_action"
            ]["selected_options"]
        ]
        selected_permissions = [
            b["value"]
            for b in body["view"]["state"]["values"]["desired_permissions"][
                "desired_permissions_action"
            ]["selected_options"]
        ]

        all_aws_actions = []
        services = []
        for action in selected_actions:
            service = action.split(":")[0]
            if service == "*":
                aws_actions = ["*"]
            else:
                aws_actions = await _get_policy_sentry_access_level_actions(
                    service, selected_permissions
                )
            all_aws_actions.extend(aws_actions)
        duration = body["view"]["state"]["values"]["duration"]["duration"][
            "selected_option"
        ]["value"]

        template_changes = {}
        resources = defaultdict(list)
        for identity in selected_identities:
            identity_hash = identity["value"]
            template = template_changes.get(identity_hash, None)
            if template:
                template = template.template
            identity_info = reverse_hash_for_arns[identity_hash]
            arn = identity_info["arn"]
            account_id = arn.split(":")[4]
            account_name = account_id
            for account in iambic_aws_accounts:
                if account["account_id"] == account_id:
                    account_name = account["account_name"]
                    break
            template_type = identity_info["template_type"]
            repo_name = identity_info["repo_name"]
            repo_relative_file_path = identity_info["repo_relative_file_path"]
            file_path = identity_info["file_path"]
            if template_type == "NOQ::AWS::IAM::Role":
                template = await iambic.aws_iam_role_add_inline_policy(
                    template_type,
                    repo_name,
                    repo_relative_file_path,
                    user_email,
                    duration,
                    all_aws_actions,
                    selected_resources,
                    account_name,
                    existing_template=template
                    # TODO: If I modify 2 roles on the same account, we need
                    # to recurse over the template to make sure both sets of changes
                    # are captured in a single template
                )
                resources[template_type].append(template.identifier)
                print(template)
                # if template.owner:
                #     user_info = await client.users_lookupByEmail(email=email)
                #     owners[template.owner] = user_info
            template_changes[identity_hash] = IambicTemplateChange(
                path=repo_relative_file_path,
                body=template.get_body(exclude_unset=False),
                template=template,
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
            tenant=self.tenant,
            request_id=request_id,
            requested_by=user_email,
            merge_on_approval=iambic_repo.merge_on_approval,
            pull_request_id=pull_request_id,
        )

        branch_name = await request_pr.create_request(
            justification, template_changes.values()
        )
        request_details = await request_pr.get_request_details()
        pr_url = request_details["pull_request_url"]
        reviewers = "engineering@noq.dev"
        channel_id = "C045MFZ2A10"
        slack_message_to_reviewers = self_service_permissions_review_blocks(
            username,
            resources,
            duration,
            reviewers,
            justification,
            pr_url,
            branch_name,
            request_id,
            user_email,
        )

        user_id = body["user"]["id"]

        await client.chat_postMessage(
            channel=user_id,
            text=(
                "Your request has been successfully submitted. "
                f"Click the link below to view more details: {pr_url}"
            ),
        )
        # TODO: Grab maessage sent to this channel and post as a comment on PR
        await client.chat_postMessage(
            channel=channel_id,
            blocks=slack_message_to_reviewers,
            text="An access request is awaiting your review.",
        )

        view_id = body["view"]["id"]
        # Update view
        await client.views_update(
            view_id=view_id,
            view=self_service_submission_success.replace(
                "{{pull_request_url}}", pr_url
            ),  # TODO change
        )

    async def select_aws_services_action(self, ack, body, logger, client):
        await ack()
        view_template = select_desired_permissions_modal
        view_template["private_metadata"] = json.dumps(
            {
                "actions": [
                    b["value"]
                    for b in body["view"]["state"]["values"]["select_services"][
                        "select_aws_services_action"
                    ]["selected_options"]
                ]
            }
        )
        await client.views_update(
            view_id=body["view"]["id"],
            hash=body["view"]["hash"],
            view=view_template,
        )
        logger.info(body)

    async def handle_request_cloud_permissions_to_resource_ack(self, ack):
        await ack(response_action="update", view=select_desired_permissions_modal)

    async def handle_request_update_or_remove_tags_ack(self, ack):
        await ack(response_action="update", view=update_or_remove_tags_modal)

    async def handle_request_update_or_remove_tags(self, logger, body, client, respond):
        tenant_config = TenantConfig(self.tenant)
        reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
            redis_key=tenant_config.iambic_hash_arn_redis_key,
            tenant=tenant,
        )

        justification = body["view"]["state"]["values"]["justification"][
            "justification"
        ]["value"]

        selected_identities = body["view"]["state"]["values"]["select_identities"][
            "select_identities_action"
        ]["selected_options"]

    async def get_slack_app(self):
        self.tenant_slack_app = TenantAsyncSlackApp(
            name=self.tenant,
            logger=logger,
            installation_store=get_installation_store(),
            signing_secret=config.get("_global_.secrets.slack.signing_secret"),
            process_before_response=True,
        )
        self.tenant_slack_app.use(create_log_request_handler(self.tenant))

        # This is the handler for the Noq App Shortcut
        self.tenant_slack_app.shortcut("noq")(
            ack=self.handle_generic_ack,
            lazy=[self.noq_command_welcome_selection],
        )
        # This is the handler for the `/noq` command
        self.tenant_slack_app.command("/noq")(
            ack=self.handle_generic_ack,
            lazy=[self.noq_command_welcome_selection],
        )

        # This handles the typeahead for resource selection, with a filter on the
        # resource type (Specified as `.*` below)
        self.tenant_slack_app.options(re.compile("^select_resources/.*"))(
            self.handle_select_resources_options_tenant
        )

        self.tenant_slack_app.action("self-service-select")(
            self.handle_self_service_select
        )

        self.tenant_slack_app.action("cancel_request")(self.cancel_request)

        self.tenant_slack_app.action(re.compile(r"create_request"))(
            ack=self.handle_request_access_to_resource_ack,
            lazy=[
                self.handle_request_access_to_resource_tenant,
            ],
        )

        self.tenant_slack_app.action("select_app_type")(self.handle_select_app_type)
        self.tenant_slack_app.action("edit_request")(
            ack=self.handle_generic_ack,
            lazy=[self.handle_edit_request],
        )
        self.tenant_slack_app.view("request_success")(self.handle_generic_ack)

        self.tenant_slack_app.view(
            "self_service_request_permissions_step_2_option_selection"
        )(
            self.handle_request_permissions_step_2_option_selection,
        )
        self.tenant_slack_app.options("select_identities_action")(
            self.handle_select_cloud_identities_options_tenant
        )

        self.tenant_slack_app.options("select_aws_services_action")(
            self.handle_select_aws_actions_options
        )

        self.tenant_slack_app.options("select_aws_resources_action")(
            self.handle_select_aws_resources_options
        )

        self.tenant_slack_app.view("request_cloud_permissions_to_resources")(
            ack=self.handle_request_cloud_permissions_to_resource_ack,
            lazy=[self.handle_request_cloud_permissions_to_resources],
        )
        self.tenant_slack_app.action("select_aws_services_action")(
            self.select_aws_services_action
        )
        self.tenant_slack_app.view("request_update_or_remove_tags")(
            ack=self.handle_request_update_or_remove_tags_ack,
            lazy=[self.handle_request_update_or_remove_tags],
        )

        return self.tenant_slack_app


# async def get_slack_app_for_tenant(tenant, enterprise_id, team_id, app_id):
#     tenant_slack_app = TenantAsyncSlackApp(
#         name=tenant,
#         logger=logger,
#         installation_store=get_installation_store(),
#         signing_secret=config.get("_global_.secrets.slack.signing_secret"),
#         process_before_response=True,
#     )
#     tenant_slack_app.use(create_log_request_handler(tenant))
#     # tenant_slack_app.middleware(partial(log_request_tenant, tenant=tenant))

#     tenant_slack_app.action("select_resources")(
#         ack=handle_generic_ack,
#         lazy=[partial(handle_select_resources_tenant, tenant=tenant)],
#     )

#     tenant_slack_app.options(re.compile("^select_resources/.*"))(
#         partial(handle_select_resources_options_tenant, tenant=tenant)
#     )

#     # tenant_slack_app.view(re.compile(r"request_access_to_resource.*"))(
#     #     ack=handle_request_access_to_resource_ack,
#     #     lazy=[
#     #         partial(
#     #             handle_request_access_to_resource_tenant,
#     #             tenant=tenant,
#     #         )
#     #     ],
#     # )
#     tenant_slack_app.shortcut("noq")(
#         ack=handle_generic_ack,
#         lazy=[partial(request_access_step_1_tenant, tenant=tenant)],
#     )
#     tenant_slack_app.command("/noq")(
#         ack=handle_generic_ack,
#         lazy=[partial(request_access_step_1_tenant, tenant=tenant)],
#     )

#     tenant_slack_app.action("self-service-select")(
#         partial(handle_self_service_select, tenant=tenant)
#     )

#     tenant_slack_app.action("cancel_request")(
#         partial(cancel_request, tenant=tenant)
#     )

#     tenant_slack_app.action(re.compile(r"create_request"))(
#         ack=handle_request_access_to_resource_ack,
#         lazy=[
#             partial(
#                 handle_request_access_to_resource_tenant,
#                 tenant=tenant,
#             )
#         ],
#     )

#     # tenant_slack_app.action("create_request")(
#     #     partial(create_request, tenant=tenant)
#     # )

#     tenant_slack_app.event("user_change")(
#         partial(handle_user_change_events, tenant=tenant)
#     )
#     tenant_slack_app.view("self_service_step_1")(
#         partial(handle_request_access_step_1_callback, tenant=tenant)
#     )
#     tenant_slack_app.view_submission("self_service_step_1")(
#         partial(handle_request_access_step_1_callback, tenant=tenant)
#     )

#     tenant_slack_app.action("select_app_type")(
#         partial(handle_select_app_type, tenant=tenant)
#     )
#     tenant_slack_app.action("edit_request")(
#         ack=handle_generic_ack,
#         lazy=[partial(handle_edit_request, tenant=tenant)],
#     )
#     tenant_slack_app.view("request_success")(handle_generic_ack)

#     # tenant_slack_app.options("select_identities_action")(
#     #     partial(handle_select_cloud_identity_request_type, tenant=tenant)
#     # )
#     tenant_slack_app.view("self_service_request_permissions_step_2_option_selection")(
#         partial(handle_request_permissions_step_2_option_selection, tenant=tenant)
#     )
#     tenant_slack_app.options("select_identities_action")(
#         partial(handle_select_cloud_identities_options_tenant, tenant=tenant)
#     )

#     tenant_slack_app.options("select_aws_services_action")(
#         partial(handle_select_aws_actions_options, tenant=tenant)
#     )

#     tenant_slack_app.options("select_aws_resources_action")(
#         partial(handle_select_aws_resources_options, tenant=tenant)
#     )

#     tenant_slack_app.view("request_cloud_permissions_to_resources")(
#         ack=handle_request_cloud_permissions_to_resource_ack,
#         lazy=[partial(handle_request_cloud_permissions_to_resources, tenant=tenant)],
#     )
#     tenant_slack_app.action("select_aws_services_action")(
#         partial(select_aws_services_action, tenant=tenant)
#     )
#     tenant_slack_app.view("request_update_or_remove_tags")(
#         ack=handle_request_update_or_remove_tags_ack,
#         lazy=[partial(handle_request_update_or_remove_tags, tenant=tenant)],
#     )
#     return tenant_slack_app


# TODO: Select Policy Group
# Policy group has substitutions that define if typeahead or string
# {{}}
#
# template_type: NOQ::AWS::PolicyTemplate
# identifier: s3_list_bucket
# properties:
#   action:
#     - s3:ListBucket
#   effect:
#     - Allow
#   resource:
#    {{NOQ::AWS::S3::Bucket/Bucket_Name}}
#   condition:
#     stringlike:
#       - {{NOQ::AWS::S3::Bucket/Bucket_Name}}/*

# template_type: NOQ::AWS::PolicyTemplate
# identifier: self_role_assumption
# properties:
#   action:
#     - sts:AssumeRole
#   effect: Allow
#   resource:
#     - {{NOQ::AWS::IAM::Role/RoleName}}

# template_type: NOQ::AWS::PolicyTemplate
# identifier: ReadSecret
# properties:
#  action:
#   - secretsmanager:GetSecretValue
#   - secretsmanager:DescribeSecret
#   - secretsmanager:ListSecretVersionIds
#   - secretsmanager:GetResourcePolicy
# effect:
#  - Allow
# resource:
# - {{NOQ::AWS::SecretsManager::Secret/Secret_Prefix}}/*
