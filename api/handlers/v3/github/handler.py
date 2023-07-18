import uuid
from typing import Optional
from urllib.parse import urljoin

from pydantic import ValidationError
from tornado.web import HTTPError

from common.config.globals import GITHUB_APP_URL
from common.github.models import GitHubInstall, GitHubOAuthState
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.iambic.utils import delete_iambic_repos, get_iambic_repo, save_iambic_repos
from common.iambic_request.utils import noq_github_app_identity
from common.lib.iambic.git import IambicGit
from common.lib.pydantic import BaseModel
from common.models import IambicRepoDetails, WebResponse
from common.tenants.models import Tenant

# TODO: Event driven could route messages to SQS and then have a worker process them. Maybe for Slack too.


class GithubRepoHandlerPost(BaseModel):
    repo_name: Optional[str]
    merge_on_approval: Optional[bool]


class GitHubOAuthHandler(BaseAdminHandler):
    async def get(self):
        state = str(uuid.uuid4())
        # Save the state to the database
        await GitHubOAuthState.create(self.ctx.db_tenant, state=state)
        url = urljoin(GITHUB_APP_URL, f"installations/new?state={state}")
        self.write(
            WebResponse(success="success", data={"github_install_url": url}).dict(
                exclude_unset=True, exclude_none=True
            )
        )
        return


class GitHubCallbackHandler(TornadoRequestHandler):
    def on_finish(self):
        if self.repo_specified:
            from common.celery_tasks.celery_tasks import app as celery_app

            # Trigger a full sync of all iambic tables/resources for the tenant
            celery_app.send_task(
                "common.celery_tasks.celery_tasks.run_full_iambic_sync_for_tenant",
                kwargs={"tenant": self.db_tenant.name},
            )

    def initialize(self):
        self.repo_specified = False
        self.db_tenant: Tenant = None

    async def get(self):
        state = self.get_argument("state", default=None)
        installation_id = self.get_argument("installation_id", default=None)
        setup_action = self.get_argument("setup_action")

        if setup_action == "request":
            # the user only request the Github Admin to approve the app installation
            self.write(
                f"Ask your GitHub administrator to approve the app installation. They’ll be redirected back to Noq to finalize it. Make sure they append state={state} to the Noq URL they are redirected back to, and to reload the page to finish the installation."
            )
            return
        elif setup_action == "install" and not state:
            # the Github Admin approve the app installation but is not the same requester
            # not using self.request.full_uri() because our local dev will see http protocol
            self.write(
                "Please retrieve the state value that was provided during the initial installation request, and append it to the URL as state=UNIQUE_VALUE. Then, reload the page to finish the installation."
            )
            return

        # Verify the state
        github_oauth_state = await GitHubOAuthState.get_by_state(state)
        if not github_oauth_state:
            raise HTTPError(400, "Invalid state")

        db_tenant: Tenant = await Tenant.get_by_id(github_oauth_state.tenant_id)

        if not db_tenant:
            raise HTTPError(400, "Invalid tenant")

        # Save the GitHub installation
        await GitHubInstall.create(tenant=db_tenant, installation_id=installation_id)
        await github_oauth_state.delete()
        iambic_git = IambicGit(db_tenant.name)
        repos = await iambic_git.get_repos()
        repo_fullnames = [
            repo.get("full_name") for repo in repos.get("repositories", [])
        ]
        if len(repo_fullnames) == 1:
            iambic_repo = IambicRepoDetails(repo_name=repo_fullnames[0])
            self.repo_specified = True
            await save_iambic_repos(
                db_tenant.name, iambic_repo, "GitHubCallbackHandler"
            )

        self.write("GitHub integration complete")
        self.db_tenant = db_tenant


class DeleteGitHubInstallHandler(BaseAdminHandler):
    async def delete(self, install_id):
        github_install = await GitHubInstall.get(self.ctx.db_tenant, install_id)
        if not github_install:
            raise HTTPError(404, "GitHub installation not found")

        await github_install.delete()
        await delete_iambic_repos(self.ctx.tenant, self.user)
        self.set_status(204)


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
                    status="success", status_code=200, data={"installed": True}
                ).dict(exclude_unset=True, exclude_none=True)
            )
        else:
            self.write(
                WebResponse(
                    status="success", status_code=200, data={"installed": False}
                ).dict(exclude_unset=True, exclude_none=True)
            )


class GithubRepoHandler(BaseAdminHandler):
    def on_finish(self):
        if self.repo_specified:
            from common.celery_tasks.celery_tasks import app as celery_app

            celery_app.send_task(
                "common.celery_tasks.celery_tasks.sync_iambic_templates_for_tenant",
                kwargs={"tenant": self.ctx.tenant},
            )

    def initialize(self):
        self.repo_specified = False

    async def get(self):
        self.set_header("Content-Type", "application/json")
        github_install = await GitHubInstall.get(self.ctx.db_tenant)
        if not github_install:
            self.write(
                WebResponse(
                    status="success",
                    status_code=200,
                    data={
                        "repos": [],
                        "configured_repo": None,
                    },
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return
        iambic_git = IambicGit(self.ctx.tenant)
        repos = await iambic_git.get_repos()
        repo_fullnames = [
            repo.get("full_name") for repo in repos.get("repositories", [])
        ]
        iambic_repos = await get_iambic_repo(self.ctx.tenant)
        if isinstance(iambic_repos, list):
            iambic_repos = iambic_repos[0]
        iambic_repo_name = iambic_repos.repo_name if iambic_repos else None
        merge_on_approval = iambic_repos.merge_on_approval if iambic_repos else False
        self.set_header("Content-Type", "application/json")
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={
                    "repos": repo_fullnames,
                    "configured_repo": iambic_repo_name,
                    "merge_on_approval": merge_on_approval,
                    "integration_config": noq_github_app_identity(),
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def post(self):
        try:
            body = GithubRepoHandlerPost.parse_raw(self.request.body)
        except ValidationError as e:
            self.set_status(400)
            self.set_header("Content-Type", "application/json")
            self.write(
                WebResponse(
                    status="failure",
                    status_code=400,
                    message="Invalid input: " + str(e),
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return
        if not body.repo_name:
            await delete_iambic_repos(self.ctx.tenant, self.user)
        else:
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
                        success="failure",
                        status_code=400,
                        message="Repository not found",
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                return

            iambic_repo = IambicRepoDetails(
                repo_name=body.repo_name, merge_on_approval=body.merge_on_approval
            )
            await save_iambic_repos(self.ctx.tenant, iambic_repo, self.user)
            self.repo_specified = True

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
