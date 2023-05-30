import uuid

from pydantic import ValidationError
from tornado.web import HTTPError

from common.config.globals import GITHUB_APP_URL
from common.github.models import GitHubInstall, GitHubOAuthState
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.iambic.utils import save_iambic_repos
from common.lib.iambic.git import IambicGit
from common.lib.pydantic import BaseModel
from common.models import IambicRepoDetails, WebResponse
from common.tenants.models import Tenant

# TODO: Need to know which repos to use, in case they grant us access to more than necessary.
# TODO: Which repo does this installation token have access to?
# TODO: Event driven could route messages to SQS and then have a worker process them. Maybe for Slack too.


class GithubRepoHandlerPost(BaseModel):
    repo_name: str


class GitHubOAuthHandler(BaseAdminHandler):
    async def get(self):
        state = str(uuid.uuid4())
        # Save the state to the database
        await GitHubOAuthState.create(self.ctx.db_tenant, state=state)
        url = f"{GITHUB_APP_URL}installations/new?state={state}"
        self.write(
            WebResponse(success="success", data={"github_install_url": url}).dict(
                exclude_unset=True, exclude_none=True
            )
        )
        return


class GitHubCallbackHandler(TornadoRequestHandler):
    async def get(self):
        state = self.get_argument("state")
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
        await GitHubInstall.create(tenant=db_tenant, installation_id=installation_id)
        await github_oauth_state.delete()
        self.write("GitHub integration complete")


class DeleteGitHubInstallHandler(BaseAdminHandler):
    async def delete(self, install_id):
        github_install = await GitHubInstall.get(self.ctx.db_tenant, install_id)
        if not github_install:
            raise HTTPError(404, "GitHub installation not found")

        await github_install.delete()
        self.set_status(204)


class GitHubEventsHandler(TornadoRequestHandler):
    async def post(self):
        pass
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


class GithubStatusHandler(BaseAdminHandler):
    async def delete(self, *args):
        tenant_install_rel = await GitHubInstall.get(self.ctx.db_tenant)
        if tenant_install_rel:
            await tenant_install_rel.delete()
        self.write(WebResponse(success="success", status_code=200).dict())

    async def get(self, *args):
        tenant_install_rel = await GitHubInstall.get(self.ctx.db_tenant)
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


class GithubRepoHandler(BaseAdminHandler):
    async def get(self):
        iambic_git = IambicGit(self.ctx.tenant)
        repos = await iambic_git.get_repos()
        self.set_header("Content-Type", "application/json")
        self.write(
            WebResponse(success="success", status_code=200, data={"repos": repos}).dict(
                exclude_unset=True, exclude_none=True
            )
        )

    async def post(self):
        try:
            body = GithubRepoHandlerPost.parse_raw(self.request.body)
        except ValidationError as e:
            self.set_status(400)
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    success="failure",
                    status_code=400,
                    message="Invalid input: " + str(e),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        iambic_git = IambicGit(self.ctx.tenant)
        repos = await iambic_git.get_repos()

        # Check if the provided repo_name exists in the repos
        if not any(
            repo["full_name"] == body.repo_name for repo in repos["repositories"]
        ):
            self.set_status(400)
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    success="failure", status_code=400, message="Repository not found"
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        iambic_repos = IambicRepoDetails(repo_name=body.repo_name)
        # TODO: We want to overwrite the existing repos if they exist
        await save_iambic_repos(self.ctx.tenant, iambic_repos, self.user)

        self.set_header("Content-Type", "application/json")
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={
                    "message": "Successfully saved repository",
                    "repo_name": body.repo_name,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )
