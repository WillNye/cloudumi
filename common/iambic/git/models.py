import asyncio
import os
import shutil
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
from common.config.tenant_config import TenantConfig
from common.github.models import GitHubInstall
from common.iambic.git.utils import get_repo_access_token, list_tenant_repo_details
from common.lib.asyncio import aio_wrapper, run_command
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
        file_paths_being_changed: Optional[list[str]] = None,
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
        self.file_paths_being_changed = file_paths_being_changed or []
        self._storage_handler = TenantFileStorageHandler(self.tenant)
        self.tenant_config = TenantConfig.get_instance(str(self.tenant.name))
        self._tenant_storage_base_path = self.tenant_config.tenant_storage_base_path
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
            ref
            for ref in getattr(self.repo.remotes, self.remote_name).refs
            if ref.name == f"{self.remote_name}/HEAD"
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

    async def clone_or_pull_git_repo(self):
        """
        Assumption is we will start with a blobless clone. Such that subsequent runs can use pull naturally.
        Now if upstream break (like rewrite history), we will fallback to replace the clone.
        """
        if os.path.exists(self.default_file_path):
            self.repo = Repo(self.default_file_path)
            await self.set_repo_auth()
            try:
                self.repo.git.checkout(self.default_branch_name)
            except Exception as err:
                # The main branch is already checked out
                if "already exists and is not an empty directory" not in err.stderr:
                    raise
            self.repo.git.reset("--hard", self.get_default_branch())
            try:
                self.repo.git.pull()
            except Exception as err:
                if "refusing to merge unrelated histories" not in err.stderr:
                    # we have to be specific; otherwise, a transient network error
                    # may cause us to blow away the directory.
                    raise
                # an upstream may have re-written history, fall back to a fresh blobless clone
                shutil.rmtree(self.default_file_path)
                await self._clone_blobless_repo()
        else:
            await self._clone_blobless_repo()

    async def _clone_blobless_repo(self):
        repo = Repo.clone_from(
            await self.get_repo_uri(),
            self.default_file_path,
            config="core.symlinks=false",
            filter="blob:none",  # also known as blobless clone
            single_branch=True,  # minimize network operation to track HEAD
        )
        self.repo = repo
        await self.set_repo_auth()

    async def set_request_branch(self, reuse_branch_repo: bool = False):
        """THIS IS A DESTRUCTIVE OPERATION.
        deletes whatever is in request_file_path and sets a new worktree for the request branch in the path
        """
        if not isinstance(self.request_file_path, str):
            raise ValueError(
                f"request_file_path must be a string, got {self.request_file_path}"
            )
        if reuse_branch_repo:
            if os.path.exists(self.request_file_path):
                self.repo = Repo(self.request_file_path)
                return
        if os.path.exists(self.request_file_path):
            await aioshutil.rmtree(self.request_file_path)

        await aiofiles.os.makedirs(
            os.path.dirname(self.request_file_path), exist_ok=True
        )

        if self.file_paths_being_changed:
            # For security, we assume that self.file_paths_being_changed contains untrusted user
            # input and is trying to run arbitrary OS commands. We need to validate that the files
            # referenced here exist in the original repo
            all_files = await run_command("git", "ls-files", cwd=self.repo.working_dir)
            all_files = set(all_files.splitlines())

            for file_path in self.file_paths_being_changed:
                if file_path not in all_files:
                    raise ValueError(
                        f"The file {file_path} does not exist in the repository"
                    )
            await run_command(
                "git",
                "clone",
                "--branch",
                self.default_branch_name,
                "--single-branch",
                "--no-checkout",
                "--depth=1",
                "--no-tags",
                "--single-branch",
                await self.get_repo_uri(),
                self.request_file_path,
            )
            await run_command(
                "git",
                "sparse-checkout",
                "init",
                "--cone",
                "--sparse-index",
                cwd=self.request_file_path,
            )
            await run_command(
                "git",
                "sparse-checkout",
                "set",
                *self.file_paths_being_changed,
                cwd=self.request_file_path,
            )
            await run_command("git", "checkout", cwd=self.request_file_path)
            await run_command(
                "git",
                "checkout",
                "-b",
                self.request_branch_name,
                cwd=self.request_file_path,
            )
        else:
            try:
                await run_command(
                    "git",
                    "worktree",
                    "add",
                    "--track",
                    f"-b{self.request_branch_name}",
                    self.request_file_path,
                    cwd=self.repo.working_dir,
                )
            except GitCommandError as err:
                # The branch already exists so create the worktree for it
                if "already exists" not in err.stderr:
                    raise
                await run_command(
                    "git",
                    "worktree",
                    "add",
                    "-f",
                    self.request_file_path,
                    self.request_branch_name,
                    cwd=self.repo.working_dir,
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
            await self.set_request_branch()  # Create the worktree or sparse-checkout and set self.repo

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
            changed_files_raw = await run_command(
                "git",
                "diff",
                "--name-only",
                self.default_branch_name,
                cwd=self.request_file_path,
            )
            changed_files = changed_files_raw.split("\n")
            for file in changed_files:
                await run_command(
                    "git",
                    "checkout",
                    f"origin/{self.default_branch_name}",
                    "--",
                    file,
                    cwd=self.request_file_path,
                )
            await run_command("git", "add", *changed_files, cwd=self.request_file_path)

        await asyncio.gather(
            *[
                _apply_template_change(template_change)
                for template_change in template_changes
            ]
        )
        for template_change in template_changes:
            files_to_change = [
                os.path.join(self.request_file_path, template_change.file_path)
            ]
            if template_change.template_body:
                await run_command(
                    "git", "add", *files_to_change, cwd=self.request_file_path
                )
            else:
                await run_command(
                    "git", "rm", *files_to_change, cwd=self.request_file_path
                )

        requesting_actor = Actor("Iambic", changed_by)
        commit_message = f"Noq Request created by: {self.requested_by}"
        await run_command(
            "git",
            "-c",
            f"user.name={requesting_actor.name}",
            "-c",
            f"user.email={requesting_actor.email}",
            "commit",
            "-m",
            commit_message,
            cwd=self.request_file_path,
        )

        if request_notes:
            await run_command(
                "git", "add", "-m", request_notes, cwd=self.request_file_path
            )
        await run_command(
            "git", "config", "pull.rebase", "false", cwd=self.request_file_path
        )
        await run_command(
            "git",
            "push",
            "--force",
            "--set-upstream",
            self.remote_name,
            self.request_branch_name,
            cwd=self.request_file_path,
        )

        if request_notes:
            await run_command(
                "git",
                "push",
                "--force",
                "--set-upstream",
                self.remote_name,
                "refs/notes/commits",
                cwd=self.request_file_path,
            )
        log.debug("Pushed changes to remote branch", **log_data)
        return self.request_branch_name

    async def create_branch(
        self,
        request_id: str,
        requested_by: str,
        files: list[IambicTemplateChange],
        request_notes: Optional[str] = None,
        reuse_branch_repo: bool = False,
    ) -> str:
        self.request_id = request_id
        self.requested_by = requested_by
        await self.set_request_branch(reuse_branch_repo=reuse_branch_repo)
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
            self._default_branch_name = self.get_default_branch().replace(
                f"{self.remote_name}/", ""
            )
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
        file_paths_being_changed: Optional[list[str]] = None,
    ):
        if not file_paths_being_changed:
            file_paths_being_changed = []
        file_paths_being_changed = file_paths_being_changed
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
            file_paths_being_changed=file_paths_being_changed,
        )
        await iambic_repo_instance.set_repo()
        return iambic_repo_instance
