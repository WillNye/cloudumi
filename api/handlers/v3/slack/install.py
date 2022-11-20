import re
from tornado.httputil import HTTPServerRequest
import base64
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_flow import AsyncOAuthFlow
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_bolt.response import BoltResponse
from slack_bolt.adapter.tornado.handler import set_response
from urllib.parse import urljoin
from common.config import config
from common.handlers.base import TornadoRequestHandler


class AsyncSlackEventsHandler(TornadoRequestHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def post(self):
        bolt_resp: BoltResponse = await self.app.async_dispatch(to_async_bolt_request(self.request))
        set_response(self, bolt_resp)
        return


class AsyncSlackOAuthHandler(TornadoRequestHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def get(self, *args):
        tenant = self.get_tenant_name()
        if self.app.oauth_flow is not None:  # type: ignore
            oauth_flow: AsyncOAuthFlow = self.app.oauth_flow  # type: ignore
            if not (url := config.get_tenant_specific_key(
                "url",
                tenant
            )):
                raise ValueError("No URL configured for tenant")
            oauth_flow.redirect_uri = urljoin(url, oauth_flow.redirect_uri_path)
            if self.request.path == oauth_flow.install_path:
                bolt_resp = await oauth_flow.handle_installation(to_async_bolt_request(self.request))
                cookie_splitted = bolt_resp.headers['set-cookie'][0].split(';')
                state_var = cookie_splitted[0].split('=')[1]
                tenant_encoded = base64.b64encode(tenant.encode()).decode()
                bolt_resp.body = bolt_resp.body.replace(state_var, f"{state_var}-{tenant_encoded}")
                set_response(self, bolt_resp)
                return
            elif self.request.path == oauth_flow.redirect_uri_path:
                state = self.get_query_argument("state")
                code = self.get_query_argument("code")
                # Decode tenant from the state that was passed back from Slack
                tenant = base64.b64decode(state.split('-')[-1]).decode()
                new_state = '-'.join(state.split('-')[:-1])
                self.request.query = self.request.query.replace(state, new_state)
                bolt_resp = await oauth_flow.handle_callback(to_async_bolt_request(self.request))
                # TODO: Store tenant and Slack relationship
                team_id = bolt_resp.body['team']['id']
                set_response(self, bolt_resp)

                if bolt_resp.status != 200:
                    return
                # Unfortunately, Slack isn't giving us many options to get the actual team
                # Or enterprise IDs back. 
                team_id_parse = re.search(r'team=([A-Z0-9]+)?[&\"]', bolt_resp.body)
                team_id = team_id_parse[1]
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
