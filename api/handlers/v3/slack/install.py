import re
from urllib.parse import urljoin

import tornado
from slack_bolt.adapter.tornado.handler import set_response
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_flow import AsyncOAuthFlow
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_bolt.response import BoltResponse
from tornado.httputil import HTTPServerRequest

from common.config import config
from common.handlers.base import TornadoRequestHandler
from common.lib.slack.models import (
    SlackTenantInstallRelationship,
    TenantOauthRelationship,
    get_slack_bot,
)
from common.models import WebResponse
from common.tenants.models import Tenant


class AsyncSlackEventsHandler(TornadoRequestHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def post(self):
        bolt_resp: BoltResponse = await self.app.async_dispatch(
            to_async_bolt_request(self.request)
        )
        set_response(self, bolt_resp)
        return


class AsyncSlackOAuthHandler(TornadoRequestHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def get(self, *args):
        tenant = self.get_tenant_name()
        if self.app.oauth_flow is not None:  # type: ignore
            oauth_flow: AsyncOAuthFlow = self.app.oauth_flow  # type: ignore
            if not (url := config.get_tenant_specific_key("url", tenant)):
                self.set_status(400)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=403,
                        data={"message": "Invalid tenant or OAuth state"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            oauth_flow.redirect_uri = urljoin(url, oauth_flow.redirect_uri_path)
            if self.request.path == oauth_flow.install_path:
                db_tenant = await Tenant.get_by_name(tenant)
                if not db_tenant:
                    self.set_status(400)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={"message": "Invalid tenant or OAuth state"},
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                bolt_resp = await oauth_flow.handle_installation(
                    to_async_bolt_request(self.request)
                )
                cookie_splitted = bolt_resp.headers["set-cookie"][0].split(";")
                state_var = cookie_splitted[0].split("=")[1]
                # tenant_encoded = base64.b64encode(tenant.encode()).decode()
                # bolt_resp.body = bolt_resp.body.replace(state_var, f"{state_var}-{tenant_encoded}")
                # bolt_resp.headers['set-cookie'] has the value we need
                tenant_oauth_rel = await TenantOauthRelationship.get_by_tenant(
                    db_tenant
                )
                if tenant_oauth_rel:
                    await tenant_oauth_rel.delete()
                await TenantOauthRelationship.create(db_tenant, state_var)
                set_response(self, bolt_resp)
                return
            elif self.request.path == oauth_flow.redirect_uri_path:
                # We need to determine the tenant from the state that was passed back from Slack
                state = self.get_query_argument("state")
                tenant_oauth_rel = await TenantOauthRelationship.get_by_oauth_id(state)
                if not tenant_oauth_rel:
                    self.set_status(400)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={"message": "Invalid tenant or OAuth state"},
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                tenant = await Tenant.get_by_id(tenant_oauth_rel.tenant_id)
                if not tenant:
                    self.set_status(400)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={"message": "Invalid tenant or OAuth state"},
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                # TODO: The Callback handler expects a cookie to exist with the state, but
                # Because the callback URL is different a cookie doesn't exist in the user's
                # browser for this domain.
                # Decode tenant from the state that was passed back from Slack
                self.request.headers["Cookie"] = f"slack-app-oauth-state={state}"
                bolt_resp = await oauth_flow.handle_callback(
                    to_async_bolt_request(self.request)
                )
                # TODO: Store tenant and Slack relationship

                # team_id = bolt_resp.body['team']['id']
                set_response(self, bolt_resp)

                if bolt_resp.status != 200:
                    return
                # This is so sad, but we have to parse out team_id and app_id from the body of the
                # response because slack_bolt doesn't give us another way to get it.
                match = re.search(r"team=(\w+)&id=(\w+)", bolt_resp.body)
                if not match:
                    return
                team_id = match.group(1)
                app_id = match.group(2)
                slack_bot_id = await get_slack_bot(team_id, app_id)
                await SlackTenantInstallRelationship.create(tenant, slack_bot_id)
                # Unfortunately, Slack isn't giving us many options to get the actual team
                # Or enterprise IDs back.
                # team_id_parse = re.search(r'team=([A-Z0-9]+)?[&\"]', bolt_resp.body)
                # team_id = team_id_parse[1]
                # TODO: Store tenant and Slack relationship
                # Use NoqSlackInstallationStore to store based on team ID
                # TODO: Need to get Team ID and optionally enterprise ID here
                # Hopefully not from the bolt_resp body
                return
        self.set_status(404)


def to_async_bolt_request(req: HTTPServerRequest) -> AsyncBoltRequest:
    return AsyncBoltRequest(
        body=req.body.decode("utf-8") if req.body else "",
        query=req.query,
        headers=req.headers,
    )
