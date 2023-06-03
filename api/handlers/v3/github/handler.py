import hashlib
import hmac
import json
import uuid
from typing import Optional

from pydantic import ValidationError
from tornado.web import HTTPError

from common.config.globals import GITHUB_APP_URL, GITHUB_APP_WEBHOOK_SECRET
from common.github.models import GitHubInstall, GitHubOAuthState
from common.handlers.base import BaseAdminHandler, TornadoRequestHandler
from common.iambic.utils import delete_iambic_repos, get_iambic_repo, save_iambic_repos
from common.lib.iambic.git import IambicGit
from common.lib.pydantic import BaseModel
from common.models import IambicRepoDetails, WebResponse
from common.tenants.models import Tenant

# TODO: Need to know which repos to use, in case they grant us access to more than necessary.
# TODO: Event driven could route messages to SQS and then have a worker process them. Maybe for Slack too.


class GithubRepoHandlerPost(BaseModel):
    repo_name: Optional[str]


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


# Use to verify Github App Webhook Secret Using SHA256
def calculate_signature(webhook_secret: str, payload: str) -> str:
    secret_in_bytes = bytes(webhook_secret, "utf-8")
    digest = hmac.new(
        key=secret_in_bytes, msg=payload.encode("utf-8"), digestmod=hashlib.sha256
    )
    signature = digest.hexdigest()
    return signature


def verify_signature(sig: str, payload: str) -> None:
    good_sig = calculate_signature(GITHUB_APP_WEBHOOK_SECRET, payload)
    if not hmac.compare_digest(good_sig, sig):
        raise HTTPError(400, "Invalid signature")


class GitHubEventsHandler(TornadoRequestHandler):
    async def post(self):

        # the format is in sha256=<sig>
        request_signature = self.request.headers["x-hub-signature-256"].split("=")[1]
        # because this handler is unauthenticated, always verify signature before taking action
        verify_signature(request_signature, self.request.body.decode("utf-8"))
        github_event = json.loads(self.request.body)
        github_installation_id = github_event["installation"]["id"]

        tenant_github_install = await GitHubInstall.get_with_installation_id(
            github_installation_id
        )
        if not tenant_github_install:
            raise HTTPError(400, "Unknown installation id")

        github_action = github_event["action"]
        if github_action == "deleted":
            await tenant_github_install.delete()
            self.set_status(204)
            return
        # TODO any clean up method if we need to call if webhook event
        # notify us repos is removed
        # elif github_action == "removed":
        #     repositories_removed = github_event["repositories_removed"]
        else:
            self.set_status(
                204
            )  # such that sender won't attempt to re-send the event to us again.


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
        self.set_header("Content-Type", "application/json")
        github_install = await GitHubInstall.get(self.ctx.db_tenant)
        if not github_install:
            self.write(
                WebResponse(
                    success="success",
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
        self.set_header("Content-Type", "application/json")
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={
                    "repos": repo_fullnames,
                    "configured_repo": iambic_repo_name,
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
                    success="failure",
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

            iambic_repo = IambicRepoDetails(repo_name=body.repo_name)
            await save_iambic_repos(self.ctx.tenant, iambic_repo, self.user)

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
