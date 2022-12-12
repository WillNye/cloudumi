import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import aiofiles
import aiofiles.os
import aioshutil
from git import Actor, Repo
from github import Github
from github.File import File
from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import Any
from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID
from sqlalchemy.orm import relationship

from common.config import config
from common.lib import noq_json as json
from common.lib.asyncio import aio_wrapper
from common.lib.storage import TenantFileStorageHandler
from common.pg_core.models import Base, SoftDeleteMixin

TENANT_REPO_DIR = Path(config.get("_global_.tenant_storage.base_path")).expanduser()
if not TENANT_REPO_DIR:
    raise EnvironmentError("_global_.tenant_storage.base_path must be set")

log = config.get_logger(__name__)

RequestStatus = ENUM(
    "Pending", "Approved", "Rejected", "Expired", name="RequestStatusEnum"
)


class IambicTemplateChange(PydanticBaseModel):
    path: str
    body: Union[str | None]

    def __init__(self, **kwargs):
        path = kwargs.get("path", "")
        if not path.endswith(".yaml") or not path.endswith(".yml"):
            kwargs["path"] = f"{path}.yaml"

        super(IambicTemplateChange, self).__init__(**kwargs)


class IambicRepo:
    def __init__(
        self,
        tenant: str,
        repo_name: str,
        repo_uri: str,
        request_id: str = None,
        requested_by: str = None,
        use_request_branch: bool = False,
        remote_name: str = "origin",
    ):
        self.tenant = tenant
        self.repo_name = repo_name
        self.repo_uri = repo_uri
        self.request_id = request_id
        self.requested_by = requested_by
        self.use_request_branch = use_request_branch
        self._default_file_path = os.path.join(
            TENANT_REPO_DIR, f"{self.tenant}/iambic_template_repos/{self.repo_name}"
        )
        self.remote_name = remote_name
        self.repo = None
        self._default_branch_name = None

        self._storage_handler = TenantFileStorageHandler(self.tenant)

        if use_request_branch:
            assert request_id
            assert requested_by

    async def set_request_branch(self):
        if os.path.exists(self.request_file_path):
            await aioshutil.rmtree(self.request_file_path)

        await aiofiles.os.makedirs(
            os.path.dirname(self.request_file_path), exist_ok=True
        )
        self.repo.git.worktree(
            "add", self.request_file_path, f"-b{self.request_branch_name}"
        )
        self.repo = Repo(self.request_file_path)

    async def set_repo(self, **env):
        if os.path.exists(self.file_path):
            self.repo = Repo(self.file_path)
            return
        elif not os.path.exists(self.default_file_path):
            # The repo isn't on disk so we need to clone it before proceeding
            log.debug(
                "Cloning repo", dict(tenant=self.tenant, request_id=self.request_id)
            )
            self.repo = await aio_wrapper(
                Repo.clone_from,
                self.repo_uri,
                self.default_file_path,
                env=env,
                config="core.symlinks=false",
            )
        else:
            self.repo = Repo(self.default_file_path)
            # The repo has been cloned but the worktree doesn't exist yet
            # So, we want to pull the latest changes before we create the worktree
            await self.pull_default_branch()

        if self.use_request_branch:
            log.debug(
                "Adding tree to repo",
                dict(tenant=self.tenant, request_id=self.request_id),
            )
            await self.set_request_branch()

    async def _commit_and_push_changes(
        self, template_changes: list[IambicTemplateChange], changed_by: str
    ):
        async def _apply_template_change(change: IambicTemplateChange):
            file_path = os.path.join(self.request_file_path, change.path)
            file_body = change.body

            if not file_body and os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
            elif file_body:
                await self._storage_handler.write_file(file_path, "w", file_body)

        await asyncio.gather(
            *[
                _apply_template_change(template_change)
                for template_change in template_changes
            ]
        )
        for template_change in template_changes:
            if template_change.body:
                self.repo.index.add(
                    [os.path.join(self.request_file_path, template_change.path)]
                )
            else:
                self.repo.git.rm(
                    [os.path.join(self.request_file_path, template_change.path)]
                )

        requesting_actor = Actor("Iambic", changed_by)
        self.repo.index.commit(
            f"Made as part of Noq Request: {self.request_id} by {self.requested_by}",
            committer=requesting_actor,
            author=requesting_actor,
        )
        await aio_wrapper(
            self.repo.git.push,
            "--set-upstream",
            self.remote_name,
            self.request_branch_name,
        )
        log.debug(
            "Pushed changes to remote branch",
            dict(tenant=self.tenant, request_id=self.request_id),
        )

    async def create_branch(
        self, request_id: str, requested_by: str, files: list[IambicTemplateChange]
    ):
        self.request_id = request_id
        self.requested_by = requested_by
        await self.set_request_branch()
        await self._commit_and_push_changes(files, self.requested_by)

    async def update_branch(
        self, template_changes: list[IambicTemplateChange], updated_by: str
    ):
        await self._commit_and_push_changes(template_changes, updated_by)

    async def delete_branch(self):
        remote = self.repo.remote(name=self.remote_name)
        await aio_wrapper(remote.push, refspec=f":{self.request_branch_name}")

    async def pull_default_branch(self):
        if self.use_request_branch:
            self.use_request_branch = False
            await self.set_repo()

        remote = self.repo.remote(name=self.remote_name)
        await aio_wrapper(remote.pull, refspec=f":{self.default_branch_name}")

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
            TENANT_REPO_DIR,
            f"{self.tenant}/iambic_template_user_workspaces/{self.requested_by}/{self.repo_name}/{self.request_branch_name}",
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


class GitComment(PydanticBaseModel):
    id: str
    user: str
    body: str
    in_reply_to_id: str = None


class PullRequestFile(PydanticBaseModel):
    filename: str
    status: str
    additions: int
    body: str
    previous_body: Optional[str] = None


class BasePullRequest(PydanticBaseModel):
    """
    To Implement:
    - Overload init to set self.repo_uri and self.pr_provider
    - Implement load_pr
    - Implement _create_request
    - Implement _update_request
    - Implement _merge_request
    - Implement _reject_request

    Details on method responsibilities are defined within the stubbed out methods in BasePullRequest
    """

    tenant: str
    repo_name: str
    pull_request_id: int = None
    request_id: str = None
    requested_by: str = None

    title: str = None
    description: str = None
    comments: list[GitComment] = None
    files: list[PullRequestFile] = None
    mergeable: bool = None
    merge_on_approval: bool
    merged_at: datetime = None
    closed_at: datetime = None

    pr_provider: Any = None
    pr_obj: Any = None
    """
    Just a quick note. repo isn't thread safe but that's ok.

    Why isn't it thread safe:
        repo could be in reference to the default branch or the request branch.
        This just means it isn't safe for the instance not globally

    Why is it ok:
         We only use the request branch for file updates
         We'll never be updating the request at the same time we're creating, retrieving, merging, or rejecting it
    """
    repo: Any = None
    repo_uri: Any = None

    async def load_pr(self):
        """
        Requires:
        - pull_request_id set
        - repo_uri set

        Responsible for:
        - Loading the PR object from the provider
        - Setting the instance attributes title, description, files, comments, mergeable, closed_at, and merged_at
        """
        raise NotImplementedError

    async def add_comment(
        self, commented_by: str, body: str, original_comment_id: str = None
    ):
        raise NotImplementedError

    async def update_comment(self, comment_id: int, body: str):
        raise NotImplementedError

    async def delete_comment(self, comment: str):
        raise NotImplementedError

    async def _set_repo(self, use_request_branch: bool, force: bool = False):
        if force or not self.repo:
            self.repo: IambicRepo = IambicRepo(
                tenant=self.tenant,
                repo_name=self.repo_name,
                repo_uri=self.repo_uri,
                request_id=self.request_id,
                requested_by=self.requested_by,
                use_request_branch=use_request_branch,
            )
            await self.repo.set_repo()

    async def _create_request(self):
        """
        Requires:
        - repo_uri set

        Responsible for:
        - Creating the PR
        - Setting pr_obj
        - Setting pull_request_id
        """
        raise NotImplementedError

    async def create_request(
        self,
        description: str,
        template_changes: list[IambicTemplateChange],
    ):
        await self._set_repo(use_request_branch=False)

        self.title = f"Noq Self Service Request: {self.request_id} on behalf of {self.requested_by}"
        self.description = description
        await self.repo.create_branch(
            self.request_id, self.requested_by, template_changes
        )
        await self._create_request()

    async def _update_request(self):
        """
        Responsible for:
        - Updating the PR description
        """
        raise NotImplementedError

    async def update_request(
        self,
        updated_by: str,
        description: str = None,
        template_changes: list[IambicTemplateChange] = None,
    ):
        await self._set_repo(use_request_branch=True, force=True)
        await self.load_pr()

        if description and self.description != description:
            self.description = description
            await self._update_request()

        if template_changes:
            await self.repo.update_branch(template_changes, updated_by)

    async def _merge_request(self):
        """
        Responsible for:
        - Merging the PR
        """
        raise NotImplementedError

    async def merge_request(self):
        await self.load_pr()

        if self.mergeable and self.merge_on_approval:
            await self._merge_request()
            await self.repo.delete_branch()
            await self.repo.pull_default_branch()
        elif self.mergeable and not self.merge_on_approval:
            # TODO: Return something to let user know they need to merge the PR manually
            pass
        elif not self.merged_at:
            raise Exception("PR can not be merged")

    async def _reject_request(self):
        """
        Responsible for:
        - Closing the PR
        """
        raise NotImplementedError

    async def reject_request(self):
        log.debug(
            "Rejecting request", dict(tenant=self.tenant, request_id=self.request_id)
        )
        await self.load_pr()
        await self._reject_request()
        await self._set_repo(use_request_branch=False)
        await self.repo.delete_branch()

    async def get_request_details(self):
        if self.pull_request_id and not self.files:
            await self.load_pr()

        return self.dict()

    def dict(
        self,
        **kwargs,
    ) -> dict:
        required_keys_to_exclude = {
            "pr_provider",
            "pr_obj",
            "repo",
            "repo_uri",
        }
        if exclude := kwargs.get("exclude"):
            if not isinstance(exclude, set):
                exclude = set(exclude) if isinstance(exclude, list) else {exclude}

            exclude.update(required_keys_to_exclude)
            kwargs["exclude"] = exclude
        else:
            kwargs["exclude"] = required_keys_to_exclude

        return json.loads(json.dumps(super().dict(**kwargs)))


class GitHubPullRequest(BasePullRequest):
    def __init__(self, access_token: str, **kwargs):
        super(BasePullRequest, self).__init__(**kwargs)
        repo_name = kwargs["repo_name"]
        self.repo_uri = f"https://oauth:{access_token}@github.com/{repo_name}"
        self.pr_provider = Github(access_token).get_repo(repo_name)

    async def _get_file_as_pr_file(
        self, file: File, sha: str, previous_sha: str
    ) -> PullRequestFile:
        filename = file.filename
        previous_filename = file.previous_filename or filename

        if not self.merged_at and not self.closed_at:
            # Read from local file system if the request is still open
            path = os.path.join(self.repo.request_file_path, filename)
            body = await self.repo.storage_handler.read_file(path, "r")

            previous_path = os.path.join(self.repo.default_file_path, previous_filename)
            if os.path.exists(previous_path):
                previous_body = await self.repo.storage_handler.read_file(
                    previous_path, "r"
                )
            else:
                previous_body = ""

        else:
            # Otherwise, we need to resolve the relevant shas and use those
            body = await aio_wrapper(self.pr_provider.get_contents, filename, ref=sha)
            body = body.decoded_content.decode("utf-8")

            if file.status == "added":
                previous_body = ""
            else:
                previous_body = await aio_wrapper(
                    self.pr_provider.get_contents, previous_filename, ref=previous_sha
                )
                previous_body = previous_body.decoded_content.decode("utf-8")

        return PullRequestFile(
            body=body, previous_body=previous_body, **getattr(file, "_rawData")
        )

    async def load_pr(self):
        assert self.pull_request_id
        if not self.repo:
            await self._set_repo(False)
        self.pr_obj = await aio_wrapper(self.pr_provider.get_pull, self.pull_request_id)
        self.title = self.pr_obj.title
        self.description = self.pr_obj.body
        self.mergeable = self.pr_obj.mergeable
        self.merged_at = self.pr_obj.merged_at
        self.closed_at = self.pr_obj.closed_at

        self.comments = []
        for comments in await asyncio.gather(
            aio_wrapper(self.pr_obj.get_comments),
            aio_wrapper(self.pr_obj.get_issue_comments),
        ):
            for comment in comments:
                self.comments.append(
                    GitComment(
                        id=comment.id,
                        user=comment.user.login,
                        body=comment.body,
                        in_reply_to_id=getattr(comment, "in_reply_to", None),
                    )
                )

        previous_sha = None
        if until := self.merged_at or self.closed_at:
            commit_shas = [
                commit.sha for commit in (await aio_wrapper(self.pr_obj.get_commits))
            ]
            if merge_sha := self.pr_obj.merge_commit_sha:
                commit_shas.append(merge_sha)
            previous_sha = await self.repo.get_main_sha(commit_shas, until)

        files = await aio_wrapper(self.pr_obj.get_files)
        sha = self.pr_obj.merge_commit_sha or self.pr_obj.head.sha
        self.files = list(
            await asyncio.gather(
                *[self._get_file_as_pr_file(file, sha, previous_sha) for file in files]
            )
        )

    async def add_comment(
        self, commented_by: str, body: str, original_comment_id: str = None
    ):
        raise NotImplementedError

    async def update_comment(self, comment_id: int, body: str):
        raise NotImplementedError

    async def delete_comment(self, comment_id: int):
        raise NotImplementedError

    async def _create_request(self):
        self.pr_obj = await aio_wrapper(
            self.pr_provider.create_pull,
            title=self.title,
            body=self.description,
            head=self.repo.request_branch_name,
            base=self.repo.default_branch_name,
        )
        self.pull_request_id = self.pr_obj.number

    async def _update_request(self):
        await aio_wrapper(
            self.pr_obj.edit,
            body=self.description,
        )

    async def _merge_request(self):
        await aio_wrapper(self.pr_obj.merge)

    async def _reject_request(self):
        await aio_wrapper(self.pr_obj.edit, state="closed")


class Request(SoftDeleteMixin, Base):
    __tablename__ = "request"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_name = Column(String)
    pull_request_id = Column(Integer)
    tenant = Column(String)
    status = Column(RequestStatus, default="Pending")

    allowed_approvers = Column(ARRAY(String), default=dict)
    approved_by = Column(ARRAY(String), default=dict)
    rejected_by = Column(String, nullable=True)

    comments = relationship(
        "RequestComment",
        back_populates="request",
        cascade="all, delete-orphan",
        uselist=True,
        order_by="RequestComment.created_at",
    )

    __table_args__ = (
        Index("request_tenant_created_at_idx", "tenant", "deleted", "created_at"),
        Index(
            "request_tenant_with_status_created_at_idx",
            "tenant",
            "status",
            "deleted",
            "created_at",
        ),
        Index(
            "request_created_by_created_at_idx",
            "tenant",
            "deleted",
            "created_by",
            "created_at",
        ),
        Index(
            "request_created_by_with_status_created_at_idx",
            "tenant",
            "status",
            "deleted",
            "created_by",
            "created_at",
        ),
    )


class RequestComment(SoftDeleteMixin, Base):
    __tablename__ = "request_comment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    body = Column(String)
    request_id = Column(UUID(as_uuid=True), ForeignKey("request.id"), nullable=False)

    request = relationship("Request", back_populates="comments")

    __table_args__ = (
        Index("request_comment_created_at_idx", "request_id", "deleted", "created_at"),
    )

    def dict(self):
        return dict(
            id=self.id,
            body=self.body,
            created_by=self.created_by,
            created_at=self.created_at,
        )
