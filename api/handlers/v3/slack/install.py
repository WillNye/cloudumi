from urllib.parse import urljoin

import tornado
import ujson as json
from slack_bolt.adapter.tornado.handler import set_response
from slack_bolt.async_app import AsyncApp
from slack_bolt.oauth.async_oauth_flow import AsyncOAuthFlow
from slack_bolt.request.async_request import AsyncBoltRequest
from slack_bolt.response import BoltResponse
from tornado.httputil import HTTPServerRequest

from common.config import config
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.lib.auth import is_tenant_admin
from common.lib.slack.app import TenantSlackApp
from common.lib.slack.models import (
    SlackTenantInstallRelationship,
    TenantOauthRelationship,
    get_slack_bot,
    get_tenant_from_team_id,
)
from common.lib.web import handle_generic_error_response
from common.models import WebResponse
from common.tenants.models import Tenant


class AsyncSlackEventsHandler(TornadoRequestHandler):
    """Slack Events Callback Handler

    Must stay unauthenticated in order for Slack to call back.
    Localtunnel is a good tool to test this locally.

    :param TornadoRequestHandler:
    """

    def check_xsrf_cookie(self) -> None:
        pass

    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app
        if self.request.body_arguments:
            try:
                self.slack_team_id = self.request.body_arguments["team_id"][0].decode(
                    "utf-8"
                )
                self.app_id = self.request.body_arguments["api_app_id"][0].decode(
                    "utf-8"
                )
                self.enterprise_id = None
            except KeyError:
                self.slack_team_id = None
                self.app_id = None
                self.enterprise_id = None
            if not self.slack_team_id:
                try:
                    payload = json.loads(self.request.body_arguments["payload"][0])
                    self.slack_team_id = payload["team"]["id"]
                    self.app_id = payload["api_app_id"]
                    self.enterprise_id = None
                except KeyError:
                    self.slack_team_id = None
                    self.app_id = None
                    self.enterprise_id = None
        else:
            body = tornado.escape.json_decode(self.request.body)
            self.slack_team_id = body.get("team_id")
            self.app_id = body.get("api_app_id")
            self.enterprise_id = None
        self.slack_app = None

    async def post(self):
        if self.slack_team_id:
            tenant = await get_tenant_from_team_id(self.slack_team_id)
            if tenant:
                self.tenant = tenant.name
                self.slack_app = await TenantSlackApp(
                    self.tenant, self.enterprise_id, self.slack_team_id, self.app_id
                ).get_slack_app()
                # self.slack_app = await get_slack_app_for_tenant(
                #     self.tenant, self.enterprise_id, self.slack_team_id, self.app_id
                # )
        if self.slack_app:
            bolt_resp: BoltResponse = await self.slack_app.async_dispatch(
                to_async_bolt_request(self.request)
            )
        else:
            bolt_resp: BoltResponse = await self.app.async_dispatch(
                to_async_bolt_request(self.request)
            )
        set_response(self, bolt_resp)
        return


class AsyncSlackInstallHandler(BaseAdminHandler):
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
                bolt_req = to_async_bolt_request(self.request)
                url = await oauth_flow.build_authorize_url("", bolt_req)
                state = await oauth_flow.issue_new_state(bolt_req)
                url = await oauth_flow.build_authorize_url(state, bolt_req)
                set_cookie_value = (
                    oauth_flow.settings.state_utils.build_set_cookie_for_new_state(
                        state
                    )
                )
                cookie_splitted = set_cookie_value.split(";")
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
                self.write(
                    WebResponse(
                        success="success", data={"slack_install_url": url}
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                return
        self.set_status(404)


class AsyncSlackHandler(BaseAdminHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def delete(self, *args):
        tenant_name = self.get_tenant_name()
        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant_name,
        }

        if not is_tenant_admin(self.user, self.groups, tenant_name):
            errors = ["User is not authorized to access this endpoint."]
            generic_error_message = "User is not authorized to access this endpoint."
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return

        tenant = await Tenant.get_by_name(tenant_name)
        tenant_install_rel = await SlackTenantInstallRelationship.get_by_tenant(tenant)
        if tenant_install_rel:
            await tenant_install_rel.delete()
        self.write(WebResponse(success="success", status_code=200).dict())

    async def get(self, *args):
        tenant_name = self.get_tenant_name()
        log_data = {
            "function": f"{type(self).__name__}.{__name__}",
            "user": self.user,
            "message": "Retrieving information",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "tenant": tenant_name,
        }

        if not is_tenant_admin(self.user, self.groups, tenant_name):
            errors = ["User is not authorized to access this endpoint."]
            generic_error_message = "User is not authorized to access this endpoint."
            await handle_generic_error_response(
                self, generic_error_message, errors, 403, "unauthorized", log_data
            )
            return

        tenant = await Tenant.get_by_name(tenant_name)
        tenant_install_rel = await SlackTenantInstallRelationship.get_by_tenant(tenant)
        if tenant_install_rel:
            self.write(
                WebResponse(
                    success="success", status_code=200, data={"installed": True}
                ).dict(exclude_unset=True, exclude_none=True)
            )
        else:
            self.write(
                WebResponse(
                    success="success", status_code=200, data={"installed": False}
                ).dict(exclude_unset=True, exclude_none=True)
            )


class AsyncSlackInstallHandlerOld(BaseAdminHandler):
    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def get(self, *args):
        # TODO: Make sure they are admin before they click install link
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
        self.set_status(404)


class AsyncSlackOAuthHandler(TornadoRequestHandler):
    """Slack Callback Handler

    Must stay unauthenticated in order for Slack to call back.
    Localtunnel is a good tool to test this locally.

    :param TornadoRequestHandler:
    """

    def initialize(self, app: AsyncApp):  # type: ignore
        self.app = app

    async def get(self, *args):
        # TODO: Make sure they are admin before they click install link
        tenant = self.get_tenant_name()
        if self.app.oauth_flow is not None:  # type: ignore
            oauth_flow: AsyncOAuthFlow = self.app.oauth_flow  # type: ignore
            if self.request.path == oauth_flow.install_path:
                tenant = self.get_tenant_name()
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
                bolt_request = to_async_bolt_request(self.request)
                bolt_resp = await oauth_flow.handle_callback(bolt_request)
                # TODO: Store tenant and Slack relationship

                # team_id = bolt_resp.body['team']['id']
                set_response(self, bolt_resp)

                if bolt_resp.status != 200:
                    return

                # through the magic of custom success handler, it sets the info into bolt_request.context
                team_id = bolt_request.context.get("team_id")
                app_id = bolt_request.context.get("app_id")
                if not team_id or not app_id:
                    # what's the appropriate message mechanism?
                    # the response already is rended by user,
                    # but some very sad issue that the success handler
                    # did not setup team_id and app_id correctly.
                    log_data = {
                        "function": f"{type(self).__name__}.{__name__}",
                        "user": self.user,
                        "message": "Slack App installation flow missing team_id or app_id",
                        "user-agent": self.request.headers.get("User-Agent"),
                        "request_id": self.request_uuid,
                        "tenant": tenant,
                    }

                    errors = ["Slack App installation flow missing team_id or app_id"]
                    generic_error_message = (
                        "Slack App installation flow missing team_id or app_id"
                    )
                    await handle_generic_error_response(
                        self,
                        generic_error_message,
                        errors,
                        500,
                        "unauthorized",
                        log_data,
                    )
                    return

                slack_bot = await get_slack_bot(team_id, app_id)
                await SlackTenantInstallRelationship.create(tenant, slack_bot.id)
                return
        self.set_status(404)


def to_async_bolt_request(req: HTTPServerRequest) -> AsyncBoltRequest:
    return AsyncBoltRequest(
        body=req.body.decode("utf-8") if req.body else "",
        query=req.query,
        headers=req.headers,
    )
