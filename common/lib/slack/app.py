import datetime
import logging
import re
import time
from collections import defaultdict
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
from common.iambic_request.request_crud import (
    create_request,
    get_request,
    update_request,
)
from common.iambic_request.utils import get_iambic_pr_instance, get_iambic_repo
from common.lib.asyncio import aio_wrapper
from common.lib.aws.typeahead_cache import get_all_resource_arns
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.change_request import _get_policy_sentry_access_level_actions
from common.lib.iambic.git import IambicGit
from common.lib.redis import RedisHandler
from common.lib.slack.models import BOTS_TABLE, INSTALLATIONS_TABLE, OAUTH_STATES_TABLE
from common.lib.slack.workflows import FRIENDLY_RESOURCE_TYPE_NAMES, SlackWorkflows
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

    return slack_app


def create_log_request_handler(tenant):
    async def _log_request(logger, body, next):
        # logger.debug(body)
        return await next()

    return _log_request


class TenantAsyncSlackApp(AsyncApp):
    pass


class TenantSlackApp:
    def __init__(self, tenant, enterprise_id, team_id, app_id):
        """
        Constructor method for the TenantSlackApp class. All tenant
        slack bots should be created through this class.

        Args:
            tenant (str): Tenant ID.
            enterprise_id (str): Enterprise ID.
            team_id (str): Team ID.
            app_id (str): App ID.
        """
        self.tenant = tenant
        self.tenant_config = TenantConfig(self.tenant)
        self.enterprise_id = enterprise_id
        self.team_id = team_id
        self.app_id = app_id
        self.tenant_slack_app = None
        self.log_data = {
            "tenant": self.tenant,
            "class": "TenantSlackApp",
        }
        self.workflows = SlackWorkflows(self.tenant)

    async def get_slack_app(self):
        """
        Retrieves the Slack app for the tenant.

        Returns:
            TenantAsyncSlackApp: A Slack app.
        """
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

        self.tenant_slack_app.action("create_access_request")(
            ack=self.handle_generic_ack,
            lazy=[
                self.handle_request_access_to_resource_tenant,
            ],
        )

        self.tenant_slack_app.action(re.compile(r"^update_access_request/.*"))(
            ack=self.handle_generic_ack,
            lazy=[
                self.handle_request_access_to_resource_tenant,
            ],
        )

        # self.tenant_slack_app.action("select_app_type")(self.handle_select_app_type)
        self.tenant_slack_app.action(re.compile(r"^update_permissions_request/.*"))(
            ack=self.handle_generic_ack,
            lazy=[self.handle_update_permissions_request],
        )
        self.tenant_slack_app.view("request_success")(self.handle_generic_ack)

        self.tenant_slack_app.action(
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

        self.tenant_slack_app.action("create_cloud_permissions_request")(
            ack=self.handle_generic_ack,
            lazy=[self.handle_request_cloud_permissions_to_resources],
        )

        self.tenant_slack_app.action(
            re.compile(r"^update_cloud_permissions_request/.*")
        )(
            ack=self.handle_generic_ack,
            lazy=[self.handle_request_cloud_permissions_to_resources],
        )
        self.tenant_slack_app.action("select_aws_services_action")(
            self.handle_generic_ack
        )
        self.tenant_slack_app.action("select_aws_resources_action")(
            self.handle_generic_ack
        )

        self.tenant_slack_app.action("select_identities_action")(
            self.handle_generic_ack
        )

        self.tenant_slack_app.options("select_aws_accounts")(
            self.handle_select_aws_accounts_options
        )

        self.tenant_slack_app.action("approve_request")(
            self.handle_approve_request_action
        )

        return self.tenant_slack_app

    async def handle_generic_ack(self, ack):
        await ack()

    async def noq_command_welcome_selection(self, ack, body, client):
        await ack()
        await client.chat_postEphemeral(
            user=body["user_id"],
            text=" ",
            blocks=self.workflows.get_self_service_step_1_blocks(),
            channel=body["channel_id"],
        )

    async def handle_approve_request_action(self, ack, body, client):
        await ack()
        action_id = body["actions"][0]["action_id"]
        request_id = action_id.split("/")[-1]
        request = await self.workflows.get_request_by_id(request_id)
        if request:
            await self.workflows.approve_request(request, body["user"]["id"], client)

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
            if slack_app_type not in FRIENDLY_RESOURCE_TYPE_NAMES.keys():
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
            friendly_name = FRIENDLY_RESOURCE_TYPE_NAMES.get(
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

        if selected_option == "aws-permissions-or-tags":
            # blocks = select_desired_permissions_blocks()
            blocks = (
                self.workflows.self_service_request_permissions_step_2_option_selection()
            )
        elif selected_option == "aws-credentials":
            blocks = self.workflows.generate_self_service_request_aws_credentials_step_2_option_selection(
                "NOQ::AWS::IdentityCenter::PermissionSet"
            )
        else:
            blocks = self.workflows.generate_self_service_step_2_app_group_access(
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

    # async def handle_request_access_to_resource_ack(self, ack):
    #     await ack(response_action="update", view=request_access_to_resource_success)

    async def handle_request_access_to_resource_tenant(
        self, body, client, logger, respond
    ):
        reverse_hash_for_templates = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_templates_reverse_hash_redis_key,
            tenant=self.tenant,
        )

        # TODO: Use original message
        # original_message = await client.conversations_history(channel=body['container']['channel_id'], limit=1, latest=body['container']['message_ts'], inclusive=True)
        # original_message_blocks = original_message['messages'][0]['blocks']
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

        update = False
        request_id = None
        actions = body["actions"][0]["value"]
        if actions.startswith("update_access_request/"):
            update = True
            request_id = actions.split("update_access_request/")[1]
        user_info = await client.users_info(user=body["user"]["id"])
        user_email = user_info["user"]["profile"]["email"]
        # selected_options = body["view"]["state"]["values"]["request_access"][
        #     "select_resources"
        # ]["selected_options"]
        selected_options = []
        resource_type = None
        dynamic_select_options = body["state"]["values"]["select_resources"]
        for k, v in dynamic_select_options.items():
            if k.startswith("select_resources/"):
                resource_type = k.split("select_resources/")[1]
                selected_options.extend(v["selected_options"])

        # Only valid for AWS
        selected_aws_accounts = (
            body["state"]["values"]
            .get("select_aws_accounts", {})
            .get("select_aws_accounts", {})
            .get("selected_options", [])
        )
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
            elif template_type == "NOQ::AWS::IdentityCenter::PermissionSet":
                template = await iambic.aws_add_user_to_permission_set(
                    template_type,
                    repo_name,
                    path,
                    user_email,
                    duration,
                    selected_aws_accounts,
                )
                resources[template_type].append(template.properties.name)
            else:
                raise Exception("Invalid Template Type")

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
                errors={
                    "select_resources": "You must select at least one resource to request access to"
                },
            )
            return

        request_notes_d = {
            "justification": justification,
            "slack_username": username,
            "slack_email": user_email,
            "selected_options": selected_options,
            "duration": duration,
            "resource_type": resource_type,
        }

        if selected_aws_accounts:
            request_notes_d["selected_aws_accounts"] = selected_aws_accounts
        request_notes = yaml.dump(request_notes_d)
        approvers = "engineering@noq.dev"
        channel_id = "C045MFZ2A10"
        db_tenant = await Tenant.get_by_name(self.tenant)
        if not db_tenant:
            raise Exception("Tenant not found")
        if update:
            res = await update_request(
                db_tenant,
                request_id,
                user_email,
                [],
                justification=justification,
                changes=template_changes,
                request_notes=request_notes,
            )

            full_request = res["request"]
            friendly_request = res["friendly_request"]

            # branch_name = original_branch_name
            # TODO: Need more detailed description
            # await request_pr.update_request(
            #     updated_by=user_email,
            #     description="Updating change",
            #     template_changes=template_changes,
            #     request_notes=request_notes,
            #     reset_branch=True,
            # )
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

        slack_message_to_reviewers = self.workflows.self_service_access_review_blocks(
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
            res = await client.chat_update(
                channel=full_request.slack_channel_id,
                ts=full_request.slack_message_id,
                text="An access request is awaiting your review. (Updated)",
                blocks=slack_message_to_reviewers,
            )

        else:
            await client.chat_postMessage(
                channel=user_id,
                text=(
                    "Your request has been successfully submitted. "
                    f"Click the link below to view more details: {pr_url}"
                ),
            )

            res = await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_message_to_reviewers,
                text="An access request is awaiting your review.",
            )
            full_request.slack_channel_id = res["channel"]
            full_request.slack_message_id = res["ts"]
            full_request.pull_requesturl = pr_url
            await full_request.write()

        permalink_res = await client.chat_getPermalink(
            channel=full_request.slack_channel_id,
            message_ts=full_request.slack_message_id,
        )
        permalink = permalink_res["permalink"]
        await respond(
            replace_original=True,
            blocks=self.workflows.get_self_service_submission_success_blocks(
                permalink, updated=update
            ),
        )

    # async def handle_select_app_type(self, ack, logger, body, client, respond):
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

    async def handle_update_permissions_request(
        self, ack, client, body, logger, respond
    ):
        # Acknowledge the action to confirm receipt
        await ack()
        db_tenant = await Tenant.get_by_name(self.tenant)
        if not db_tenant:
            log.error({**self.log_data, "error": "No tenant found"})
            return
        # print edit screen. Prefill?
        # TODO: git fetch origin 'refs/notes/*':'refs/notes/*'
        # git log --show-notes='*'
        user_info = await client.users_info(user=body["user"]["id"])
        user_email = user_info["user"]["profile"]["email"]
        iambic = IambicGit(self.tenant)
        iambic_repo = await get_iambic_repo(self.tenant)
        request_id = None
        for action in body["actions"]:
            action_id = action.get("action_id", "")
            if action_id.startswith("update_permissions_request/"):
                request_id = action_id.replace("update_permissions_request/", "")

        if not request_id:
            log.error({**self.log_data, "error": "No request id found"})
            return

        request = await get_request(db_tenant, request_id)

        if not request:
            log.error({**self.log_data, "error": "No request found"})
            return

        request_notes = yaml.load(request.request_notes)
        request_type = "access"
        if request_notes.get("selected_permissions"):
            request_type = "permissions"

        if request_type == "access":
            selected_options = json.loads(json.dumps(request_notes))["selected_options"]
            resource_type = request_notes["resource_type"]
            blocks = self.workflows.generate_self_service_step_2_app_group_access(
                resource_type,
                selected_options=selected_options,
                justification=request_notes["justification"],
                duration=request_notes["duration"],
                update=True,
                message_ts=body["message"]["ts"],
                channel_id=body["channel"]["id"],
                branch_name=request.branch_name,
                pull_request_id=request.pull_request_id,
                user_email=user_email,
                request_id=request_id,
            )
            await client.chat_postEphemeral(
                user=body["user"]["id"],
                text=" ",
                blocks=blocks,
                channel=body["channel"]["id"],
            )
        elif request_type == "permissions":
            selected_permissions = request_notes["selected_permissions"]
            blocks = self.workflows.select_desired_permissions_blocks(
                selected_permissions=selected_permissions,
                selected_identities=request_notes["selected_identities"],
                selected_resources=request_notes["selected_resources"],
                justification=request_notes["justification"],
                selected_duration=request_notes["duration"],
                update=True,
                selected_services=request_notes["selected_services"],
                request_id=request_id,
            )
            await client.chat_postEphemeral(
                user=body["user"]["id"],
                text=" ",
                blocks=blocks,
                channel=body["channel"]["id"],
            )

    async def handle_request_permissions_step_2_option_selection(
        self, respond, ack, body, logger
    ):
        # Acknowledge the action to confirm receipt
        await ack()

        # Get the value of the selected radio button
        selected_option = body["state"]["values"][
            "self_service_permissions_step_2_block"
        ]["self_service_request_permissions_step_2_option_selection"][
            "selected_option"
        ][
            "value"
        ]

        # Render step 2 conditionally based on the selected option
        if selected_option == "select_predefined_policy":
            blocks = ""
        elif selected_option == "update_inline_policies":
            blocks = self.workflows.select_desired_permissions_blocks()
        elif selected_option == "update_managed_policies":
            blocks = ""
        elif selected_option == "update_tags":
            blocks = self.workflows.generate_update_or_remove_tags_message()
        else:
            raise Exception("Invalid option selected")
        await ack(response_action="update", blocks=blocks)
        await respond(
            replace_original=True,
            text=" ",
            blocks=blocks,
        )

    async def handle_select_cloud_identities_options_tenant(
        self, ack, logger, body, client, respond
    ):
        res = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_arn_typeahead_redis_key,
            tenant=self.tenant,
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

            friendly_name = FRIENDLY_RESOURCE_TYPE_NAMES.get(
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
        services = sorted(
            list({r.split(":")[0].replace("*", "") for r in results if ":" in r})
        )
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
        await ack(options=options[:100])

    async def handle_select_aws_accounts_options(
        self, ack, logger, body, client, respond
    ):
        await ack()

        # Get the value of the selected radio button
        options = []
        account_ids_to_account_names = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_aws_account_ids_to_names,
            tenant=self.tenant,
        )

        account_ids_to_account_names["*"] = "All Accounts (*)"

        for account_id, account_name in account_ids_to_account_names.items():
            if len(options) >= 100:
                break
            if body["value"] not in account_id and body["value"] not in account_name:
                continue
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": f"{account_name} ({account_id})"[:75],
                    },
                    "value": account_name[:75],
                }
            )
        await ack(options=options)

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

        s3_bucket_redis_key = self.tenant_config.aws_s3_buckets_redis_key
        red = await RedisHandler().redis(self.tenant)
        account_ids_to_account_names = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_aws_account_ids_to_names,
            tenant=self.tenant,
        )
        all_resource_arns = await aio_wrapper(red.hkeys, resource_redis_cache_key)
        all_buckets = red.hgetall(s3_bucket_redis_key)
        options.append(
            {
                "text": {
                    "type": "plain_text",
                    "text": body["value"],
                },
                "value": body["value"],
            }
        )

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

            bucket_account_id = None
            bucket_account_name = None

            if resource.startswith("arn:aws:s3:::"):
                bucket_name = resource.split("arn:aws:s3:::")[1]
                bucket_name = bucket_name.split("/")[0]

                for account_id, buckets_j in all_buckets.items():
                    buckets = json.loads(buckets_j)
                    if bucket_name in buckets:
                        bucket_account_id = account_id
                        break
            if bucket_account_id:
                bucket_account_name = account_ids_to_account_names.get(
                    bucket_account_id
                )
            resource_name = resource[:75]
            if bucket_account_name:
                resource_name = f"{resource_name} ({bucket_account_name})"[:75]
            options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": resource_name,
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

        state = body["state"]
        # res = await retrieve_json_data_from_redis_or_s3(
        #     redis_key=tenant_config.iambic_arn_typeahead_redis_key,
        #     tenant=tenant
        # )
        iambic_aws_accounts = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_aws_accounts,
            tenant=self.tenant,
        )
        # TODO: Get account names affected by user change
        reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_hash_arn_redis_key,
            tenant=self.tenant,
        )
        justification = state["values"]["justification"]["justification"]["value"]
        iambic = IambicGit(self.tenant)
        iambic_repo = await get_iambic_repo(self.tenant)
        username = body["user"]["username"]

        update = False
        request_id = None
        actions = body["actions"][0]["value"]
        if actions.startswith("update_cloud_permissions_request/"):
            update = True
            request_id = actions.split("update_cloud_permissions_request/")[1]

        user_info = await client.users_info(user=body["user"]["id"])
        user_email = user_info["user"]["profile"]["email"]

        selected_identities = state["values"]["select_identities"][
            "select_identities_action"
        ]["selected_options"]
        selected_services_options = state["values"]["select_services"][
            "select_aws_services_action"
        ]["selected_options"]
        selected_services = [b["value"] for b in selected_services_options]
        selected_resources_options = state["values"]["select_resources"][
            "select_aws_resources_action"
        ]["selected_options"]
        selected_resources = [b["value"] for b in selected_resources_options]
        selected_permissions_options = state["values"]["desired_permissions"][
            "desired_permissions_action"
        ]["selected_options"]
        selected_permissions = [b["value"] for b in selected_permissions_options]

        all_aws_actions = []
        services = []
        for action in selected_services:
            service = action.split(":")[0]
            if service == "*":
                aws_actions = ["*"]
            else:
                try:
                    aws_actions = await _get_policy_sentry_access_level_actions(
                        service, selected_permissions
                    )
                except TypeError:  # Invalid service provided
                    pass
            all_aws_actions.extend(aws_actions)
        duration = state["values"]["duration"]["duration"]["selected_option"]["value"]
        template_type = None
        template_changes = {}
        resources = defaultdict(list)
        for identity in selected_identities:
            identity_hash = identity["value"]

            identity_info = reverse_hash_for_arns[identity_hash]
            repo_relative_file_path = identity_info["repo_relative_file_path"]
            template = template_changes.get(repo_relative_file_path, None)
            if template:
                template = template.template
            arn = identity_info["arn"]
            account_id = arn.split(":")[4]
            account_name = account_id
            for account in iambic_aws_accounts:
                if account["account_id"] == account_id:
                    account_name = account["account_name"]
                    break
            template_type = identity_info["template_type"]
            repo_name = identity_info["repo_name"]
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
            template_changes[repo_relative_file_path] = IambicTemplateChange(
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

        request_notes = yaml.dump(
            {
                "justification": justification,
                "slack_username": username,
                "slack_email": user_email,
                "selected_identities": selected_identities,
                "selected_services": selected_services_options,
                "selected_resources": selected_resources_options,
                "selected_permissions": selected_permissions_options,
                "duration": duration,
                "template_type": template_type,
            }
        )
        reviewers = "engineering@noq.dev"
        channel_id = "C045MFZ2A10"

        db_tenant = await Tenant.get_by_name(self.tenant)
        if not db_tenant:
            raise Exception("Tenant not found")
        if update:
            res = await update_request(
                db_tenant,
                request_id,
                user_email,
                [],
                justification=justification,
                changes=list(template_changes.values()),
                request_notes=request_notes,
            )

            full_request = res["request"]
            friendly_request = res["friendly_request"]
        else:
            res = await create_request(
                db_tenant,
                user_email,
                justification,
                list(template_changes.values()),
                request_method="SLACK",
                slack_username=username,
                slack_email=user_email,
                duration=duration,
                resource_type=template_type,
                request_notes=request_notes,
            )
            full_request = res["request"]
            friendly_request = res["friendly_request"]
            # branch_name  = await request_pr.create_request(justification, template_changes, request_notes=request_notes)

        pr_url = friendly_request["pull_request_url"]

        slack_message_to_reviewers = (
            self.workflows.self_service_permissions_review_blocks(
                username,
                resources,
                duration,
                reviewers,
                justification,
                pr_url,
                full_request.branch_name,
                full_request.id,
                user_email,
            )
        )

        user_id = body["user"]["id"]
        if update:
            res = await client.chat_update(
                channel=full_request.slack_channel_id,
                ts=full_request.slack_message_id,
                text="An access request is awaiting your review. (Updated)",
                blocks=slack_message_to_reviewers,
            )
        else:
            await client.chat_postMessage(
                channel=user_id,
                text=(
                    "Your request has been successfully submitted. "
                    f"Click the link below to view more details: {pr_url}"
                ),
            )

            res = await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_message_to_reviewers,
                text="An access request is awaiting your review.",
            )
            full_request.slack_channel_id = res["channel"]
            full_request.slack_message_id = res["ts"]
            full_request.pull_requesturl = pr_url
            await full_request.write()

        permalink_res = await client.chat_getPermalink(
            channel=full_request.slack_channel_id,
            message_ts=full_request.slack_message_id,
        )
        permalink = permalink_res["permalink"]
        await respond(
            replace_original=True,
            blocks=self.workflows.get_self_service_submission_success_blocks(
                permalink, updated=update
            ),
        )

    # async def select_aws_services_action(self, ack, body, logger, client):
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

    async def handle_request_update_or_remove_tags(self, logger, body, client, respond):
        reverse_hash_for_arns = await retrieve_json_data_from_redis_or_s3(
            redis_key=self.tenant_config.iambic_hash_arn_redis_key,
            tenant=self.tenant,
        )

        justification = body["view"]["state"]["values"]["justification"][
            "justification"
        ]["value"]

        selected_identities = body["view"]["state"]["values"]["select_identities"][
            "select_identities_action"
        ]["selected_options"]


# TODO: Select Policy Group
# Policy group has substitutions that define if typeahead or string
# {{}}
# iampulse.com has good examples of sane policies
#
# template_type: NOQ::AWS::PolicyTemplate
# identifier: s3_list_bucket
# description: blah
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
#  - {{NOQ::AWS::SecretsManager::Secret/Secret_Prefix}}/*
