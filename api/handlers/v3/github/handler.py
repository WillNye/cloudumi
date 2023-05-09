import uuid

from tornado.web import HTTPError

from common.config import config
from common.github.models import GitHubInstall, GitHubOAuthState
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.tenants.models import Tenant

GITHUB_OAUTH_URL = "https://github.com/login/oauth/"
GITHUB_APP_URL = config.get("_global_.secrets.github_app.app_url")
GITHUB_APP_ID = config.get("_global_.secrets.github_app.app_id")
GITHUB_CLIENT_ID = config.get("_global_.secrets.github_app.client_id")
GITHUB_CLIENT_SECRET = config.get("_global_.secrets.github_app.client_secret")


# TODO: Need to know which repos to use, in case they grant us access to more than necessary.
# TODO: Which repo does this installation token have access to?
# TODO: Event driven could route messages to SQS and then have a worker process them. Maybe for Slack too.


class GitHubOAuthHandler(BaseAdminHandler):
    async def get(self):
        state = str(uuid.uuid4())
        # Save the state to the database
        await GitHubOAuthState.create(self.ctx.db_tenant, state=state)

        self.redirect(f"{GITHUB_APP_URL}installations/new?state={state}")


class GitHubCallbackHandler(TornadoRequestHandler):
    async def get(self):
        state = self.get_argument("state")
        # setup_action = self.get_argument("setup_action")
        installation_id = self.get_argument("installation_id")
        # TODO: Try repository because it might come here.

        # Verify the state
        github_oauth_state = await GitHubOAuthState.get_by_state(state)
        if not github_oauth_state:
            raise HTTPError(400, "Invalid state")

        db_tenant = await Tenant.get_by_id(github_oauth_state.tenant_id)

        if not db_tenant:
            raise HTTPError(400, "Invalid tenant")

        # Save the GitHub installation
        # TODO: rename access_token to installation_id
        await GitHubInstall.create(tenant=db_tenant, access_token=installation_id)
        await github_oauth_state.delete()
        self.write("GitHub integration complete")
        print("here")
        # Exchange installation id for installation token/access token/ whatever
        # _get_installation_token function
        # https://github.com/noqdev/iambic/blob/main/iambic/plugins/v0_1_0/github/github_app.py
        # TODO: Return some success message


class DeleteGitHubInstallHandler(BaseAdminHandler):
    async def delete(self, install_id):
        github_install = await GitHubInstall.get(self.ctx.db_tenant, install_id)
        if not github_install:
            raise HTTPError(404, "GitHub installation not found")

        await github_install.delete()
        self.set_status(204)


class GitHubEventsHandler(TornadoRequestHandler):
    async def post(self):
        # 1. Verify the payload signature
        # https://github.com/noqdev/iambic/blob/main/iambic/plugins/v0_1_0/github/github_app.py#L141
        # 2. Gate on `installation.id` to find the tenant
        print("here")
        # 3. Check if valid IAMbic repo for tenant
        # 4. Rock on
        # TODO: Make sure Github is not resending events for non-500 status codes that we return
        # TODO: Figure out how to rotate private key.
        # example body

        # TODO: Validate Webhook Secret to verify signature
        # Code: https://github.com/noqdev/iambic/blob/main/iambic/plugins/v0_1_0/github/github_app.py
