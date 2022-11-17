from tornado.httputil import HTTPServerRequest

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

    async def get(self):
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
                set_response(self, bolt_resp)
                return
            elif self.request.path == oauth_flow.redirect_uri_path:
                bolt_resp = await oauth_flow.handle_callback(to_async_bolt_request(self.request))
                set_response(self, bolt_resp)
                return
        self.set_status(404)


def to_async_bolt_request(req: HTTPServerRequest) -> AsyncBoltRequest:
    return AsyncBoltRequest(
        body=req.body.decode("utf-8") if req.body else "",
        query=req.query,
        headers=req.headers,
    )
