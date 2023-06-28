import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

import aiofiles
import aiofiles.os
import aioshutil
import pytz
from git import Actor, Repo
from git.exc import GitCommandError

from common.config import config
from common.config.globals import TENANT_STORAGE_BASE_PATH
from common.github.models import GitHubInstall
from common.iambic.git.utils import get_repo_access_token, list_tenant_repo_details
from common.lib.asyncio import aio_wrapper
from common.lib.storage import TenantFileStorageHandler
from common.models import IambicRepoDetails, IambicTemplateChange
from common.tenants.models import Tenant  # noqa: F401

log = config.get_logger(__name__)

CURRENTLY_SUPPORTED_GIT_PROVIDERS = {"github"}


class IambicRepo:
    def __init__(
        self,
        tenant: Tenant,
        repo_details: IambicRepoDetails,
        installation_id: str = None,
        request_id: str = None,
        requested_by: str = None,
        use_request_branch: bool = False,
        remote_name: str = "origin",
    ):
        if use_request_branch:
            assert request_id
            assert requested_by

        self.tenant = tenant
        self.repo_name = repo_details.repo_name
        if self.repo_name.endswith("/"):
            self.repo_name = self.repo_name[:-1]

        self.repo_details = repo_details
        self.request_id = request_id
        self.requested_by = requested_by
        self.use_request_branch = use_request_branch
        self.installation_id = installation_id
        self.remote_name = remote_name
        self.repo = None
        self.db_tenant = None
        self._default_branch_name = None
        self._storage_handler = TenantFileStorageHandler(self.tenant)
        self._tenant_storage_base_path = os.path.expanduser(
            os.path.join(TENANT_STORAGE_BASE_PATH, f"{tenant.name}_{tenant.id}")
        )
        tenant_repo_base_path: str = os.path.join(
            self._tenant_storage_base_path, "iambic_template_repos"
        )
        os.makedirs(os.path.dirname(tenant_repo_base_path), exist_ok=True)
        self._default_file_path = os.path.join(tenant_repo_base_path, self.repo_name)

    def is_app_connected(self) -> bool:
        """Use this function to handle the case github_app connectivity is missing

        Note: This only checks against cloudumi database knowledge and does not
        reach out to the Git provider. The Git side will have transient failure. The database
        check is more repeatable.
        """
        # do not mutate the self object in this function
        if self.repo_details.git_provider in CURRENTLY_SUPPORTED_GIT_PROVIDERS:
            return bool(self.installation_id)
        else:
            raise NotImplementedError

    async def get_repo_access_token(self) -> str:
        return await get_repo_access_token(
            self.tenant,
            repo_details=self.repo_details,
            installation_id=self.installation_id,
            default=self.repo_details.access_token,
        )

    def get_default_branch(self) -> str:
        return next(
            ref for ref in self.repo.remotes.origin.refs if ref.name == "origin/HEAD"
        ).ref.name

    async def get_last_updated(self, file_path: str) -> Optional[str]:
        if commit := next(self.repo.iter_commits(paths=file_path), None):
            return commit.committed_datetime.astimezone(pytz.UTC).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )

    def generate_repo_link(self, file_path: str) -> str:
        repo_name = self.repo_name
        default_branch = self.default_branch_name
        domain = self.repo_details.git_domain
        return f"https://{domain}/{repo_name}/blob/{default_branch}/{file_path}"

    async def set_repo_auth(self):
        for remote in self.repo.remotes:
            if "origin" in remote.name:
                with remote.config_writer as cw:
                    cw.set("url", await self.get_repo_uri())
                remote.fetch()

    async def clone_or_pull_git_repo(self):
        if os.path.exists(self.default_file_path):
            self.repo = Repo(self.default_file_path)
            await self.set_repo_auth()
            default_branch = self.get_default_branch()
            default_branch_name = default_branch.split("/")[-1]
            try:
                self.repo.git.checkout(default_branch_name)
            except Exception as err:
                # The main branch is already checked out
                if "already exists and is not an empty directory" not in err.stderr:
                    raise
            self.repo.git.reset("--hard", default_branch)
            self.repo.git.pull()
        else:
            repo = Repo.clone_from(
                await self.get_repo_uri(),
                self.default_file_path,
                config="core.symlinks=false",
            )
            self.repo = repo
            await self.set_repo_auth()

    async def set_request_branch(self):
        """THIS IS A DESTRUCTIVE OPERATION.
        deletes whatever is in request_file_path and sets a new worktree for the request branch in the path
        """
        if os.path.exists(self.request_file_path):
            await aioshutil.rmtree(self.request_file_path)

        await aiofiles.os.makedirs(
            os.path.dirname(self.request_file_path), exist_ok=True
        )
        try:
            self.repo.git.worktree(
                "add",
                "--track",
                f"-b{self.request_branch_name}",
                self.request_file_path,
            )
        except GitCommandError as err:
            # The branch already exists so create the worktree for it
            if "already exists" not in err.stderr:
                raise
            self.repo.git.worktree(
                "add", "-f", self.request_file_path, self.request_branch_name
            )

        self.repo = Repo(self.request_file_path)
        await self.set_repo_auth()

    async def set_repo(self):
        log_data = dict(
            tenant=self.tenant,
            request_id=self.request_id,
            repo=self.repo_name,
            function=f"{__name__}.{sys._getframe().f_code.co_name}",
        )
        if os.path.exists(self.file_path):
            self.repo = Repo(self.file_path)
            await self.set_repo_auth()
        elif not os.path.exists(self.default_file_path):
            # The repo isn't on disk so we need to clone it before proceeding
            log.debug({"message": "Cloning repo", **log_data})
            await self.clone_or_pull_git_repo()
        else:
            # The repo has been cloned but the worktree doesn't exist yet
            # So, we want to pull the latest changes before we create the worktree
            log.debug({"message": "Adding tree to repo", **log_data})
            await self.clone_or_pull_git_repo()  # Ensure we have the latest changes on main
            await self.set_request_branch()  # Create the worktree and set self.repo

    async def _commit_and_push_changes(
        self,
        template_changes: list[IambicTemplateChange],
        changed_by: str,
        request_notes=Optional[None],
        reset_branch: bool = False,
    ) -> str:
        log_data = dict(
            tenant=self.tenant,
            request_id=self.request_id,
            repo=self.repo_name,
            function=f"{__name__}.{sys._getframe().f_code.co_name}",
        )

        async def _apply_template_change(change: IambicTemplateChange):
            file_path = os.path.join(self.request_file_path, change.file_path)
            file_body = change.template_body

            if not file_body and os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
            elif file_body:
                await self._storage_handler.write_file(file_path, "w", file_body)

        if reset_branch:
            changed_files = self.repo.git.diff(
                "--name-only", self.default_branch_name
            ).split("\n")
            for file in changed_files:
                self.repo.git.checkout(f"origin/{self.default_branch_name}", "--", file)
            self.repo.index.add(changed_files)

        await asyncio.gather(
            *[
                _apply_template_change(template_change)
                for template_change in template_changes
            ]
        )
        for template_change in template_changes:
            if template_change.template_body:
                self.repo.index.add(
                    [os.path.join(self.request_file_path, template_change.file_path)]
                )
            else:
                self.repo.git.rm(
                    [os.path.join(self.request_file_path, template_change.file_path)]
                )

        requesting_actor = Actor("Iambic", changed_by)
        self.repo.index.commit(
            f"Noq Request created by: {self.requested_by}",
            committer=requesting_actor,
            author=requesting_actor,
        )

        if request_notes:
            self.repo.git.notes("add", "-m", request_notes)
        await aio_wrapper(self.repo.git.config, "pull.rebase", "false")
        await aio_wrapper(
            self.repo.git.push,
            "--force",
            "--set-upstream",
            self.remote_name,
            self.request_branch_name,
        )
        if request_notes:
            await aio_wrapper(
                self.repo.git.push,
                "--force",
                "--set-upstream",
                self.remote_name,
                "refs/notes/commits",
            )
        log.debug({"message": "Pushed changes to remote branch", **log_data})
        return self.request_branch_name

    async def create_branch(
        self,
        request_id: str,
        requested_by: str,
        files: list[IambicTemplateChange],
        request_notes: Optional[str] = None,
    ) -> str:
        self.request_id = request_id
        self.requested_by = requested_by
        await self.set_request_branch()
        return await self._commit_and_push_changes(
            files, self.requested_by, request_notes
        )

    async def update_branch(
        self,
        template_changes: list[IambicTemplateChange],
        updated_by: str,
        request_notes: Optional[str] = None,
        reset_branch: bool = False,
    ) -> str:
        await self.pull_current_branch()
        return await self._commit_and_push_changes(
            template_changes, updated_by, request_notes, reset_branch=reset_branch
        )

    async def delete_branch(self):
        try:
            remote = self.repo.remote(name=self.remote_name)
            await aio_wrapper(remote.push, refspec=f":{self.request_branch_name}")
        except GitCommandError as err:
            if "remote ref does not exist" not in err.stderr:
                raise

    async def pull_current_branch(self):
        branch_name = (
            self.request_branch_name
            if self.use_request_branch
            else self.default_branch_name
        )
        remote = self.repo.remote(name=self.remote_name)
        await aio_wrapper(remote.pull, refspec=f":{branch_name}")

    async def get_main_sha(self, exclude_shas: list[str], until: datetime = None):
        until = until or datetime.utcnow()
        epoch_until = int(until.timestamp())
        # 25 is just an arbitrary number that gives us some padding if there were a lot of commits on the same day
        for commit in self.repo.iter_commits(
            until=until.strftime("%b %d %Y"), max_count=len(exclude_shas) + 25
        ):
            if (
                str(commit.hexsha) not in exclude_shas
                and commit.committed_date < epoch_until
            ):
                return commit.hexsha

    async def get_file_version(self, file_path: str, sha: str):
        return await aio_wrapper(self.repo.git.show, f"{sha}:{file_path}")

    async def get_repo_uri(self):
        access_token = await self.get_repo_access_token()
        return f"https://oauth:{access_token}@github.com/{self.repo_name}"

    @property
    def storage_handler(self):
        return self._storage_handler

    @property
    def default_file_path(self):
        return self._default_file_path

    @property
    def request_file_path(self):
        assert self.request_id
        assert self.requested_by
        return os.path.join(
            self._tenant_storage_base_path,
            f"iambic_template_user_workspaces/{self.requested_by}/{self.repo_name}/{self.request_branch_name}",
        )

    @property
    def file_path(self):
        return (
            self.request_file_path
            if self.use_request_branch
            else self.default_file_path
        )

    @property
    def request_branch_name(self):
        return f"noq-self-service-{self.request_id}"

    @property
    def default_branch_name(self):
        if not self._default_branch_name:
            self._default_branch_name = next(
                ref
                for ref in getattr(self.repo.remotes, self.remote_name).refs
                if ref.name == f"{self.remote_name}/HEAD"
            ).ref.name.replace(f"{self.remote_name}/", "")

        return self._default_branch_name

    @classmethod
    async def get_all_tenant_repos(cls, tenant_name: str) -> list["IambicRepo"]:
        tenant = await Tenant.get_by_name(tenant_name)
        repo_details = list_tenant_repo_details(tenant_name)
        res = await asyncio.gather(
            *[cls.setup(tenant, repo_detail.repo_name) for repo_detail in repo_details],
            return_exceptions=True,
        )
        for repo in res:
            if isinstance(repo, Exception):
                log.error(
                    dict(
                        message="Error setting up repo",
                        tenant=tenant_name,
                        repo_name=[
                            repo_detail.repo_name for repo_detail in repo_details
                        ],
                        error=repo.__class__.__name__,
                    ),
                    # The documentation says passing just exception instance would
                    # suffice but did not work. An alternative is to pass this tuple.
                    exc_info=(type(repo), repo, repo.__traceback__),
                )
        return [repo for repo in res if not isinstance(repo, Exception)]

    @classmethod
    async def setup(
        cls,
        tenant: Tenant,
        repo_name: str,
        request_id: str = None,
        requested_by: str = None,
        use_request_branch: bool = False,
        remote_name: str = "origin",
    ):
        all_repo_details = list_tenant_repo_details(tenant.name)
        repo_details = next(
            (repo for repo in all_repo_details if repo.repo_name == repo_name), None
        )
        assert bool(
            repo_details
        ), f"Repo {repo_name} not found for tenant {tenant.name}"

        installation_id = None
        if repo_details.git_provider == "github":
            gh_install = await GitHubInstall.get(tenant)
            if gh_install:
                installation_id = gh_install.installation_id
            else:
                raise AttributeError(
                    f"No GitHub installation found for tenant {tenant.name} github repo {repo_name}"
                )

        iambic_repo_instance = cls(
            tenant=tenant,
            repo_details=repo_details,
            remote_name=remote_name,
            installation_id=installation_id,
            request_id=request_id,
            requested_by=requested_by,
            use_request_branch=use_request_branch,
        )
        await iambic_repo_instance.set_repo()
        return iambic_repo_instance
