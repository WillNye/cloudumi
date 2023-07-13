import asyncio
import os
import sys
import uuid
from datetime import datetime
from typing import Optional, Union

from cryptography.hazmat.primitives import serialization
from github import Github
from github.File import File
from iambic.core.utils import jws_encode_with_past_time
from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import Any
from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID
from sqlalchemy.orm import relationship

from common.config import config
from common.config.globals import ASYNC_PG_SESSION, GITHUB_APP_APPROVE_PRIVATE_PEM_1
from common.iambic.git.models import IambicRepo
from common.lib import noq_json as json
from common.lib.asyncio import aio_wrapper
from common.models import IambicTemplateChange
from common.pg_core.models import Base, SoftDeleteMixin
from common.tenants.models import Tenant  # noqa: F401

log = config.get_logger(__name__)

RequestStatus = ENUM(
    "Pending",
    "Pending in Git",
    "Applied",
    "Approved",
    "Rejected",
    "Expired",
    "Running",
    "Failed",
    name="RequestStatusEnum",
)


class GitComment(PydanticBaseModel):
    id: str
    user: str
    body: str
    created_at: datetime
    in_reply_to_id: str = None


class PullRequestFile(PydanticBaseModel):
    file_path: str
    status: str
    additions: int
    template_body: str
    previous_body: Optional[str] = None


class BasePullRequest(PydanticBaseModel):
    """
    To Implement:
    - Implement load_pr
    - Implement _create_request
    - Implement _update_request
    - Implement _reject_request

    Details on method responsibilities are defined within the stubbed out methods in BasePullRequest
    """

    tenant: Tenant
    """
    Just a quick note. repo isn't thread safe but that's ok.

    Why isn't it thread safe:
        repo could be in reference to the default branch or the request branch.
        This just means it isn't safe for the instance not globally

    Why is it ok:
         We only use the request branch for file updates
         We'll never be updating the request at the same time we're creating, retrieving, merging, or rejecting it
    """
    iambic_repo: IambicRepo

    pull_request_id: int = None
    pull_request_url: str = None
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

    class Config:
        arbitrary_types_allowed = True

    async def load_pr(self):
        """
        Requires:
        - pull_request_id set

        Responsible for:
        - Loading the PR object from the provider
        - Setting the instance attributes title, description, files, comments, mergeable, closed_at, and merged_at
        """
        raise NotImplementedError

    async def add_comment(
        self, body: str, commented_by: str = None, original_comment_id: str = None
    ):
        raise NotImplementedError

    async def update_comment(self, comment_id: int, body: str):
        raise NotImplementedError

    async def delete_comment(self, comment: str):
        raise NotImplementedError

    async def _create_request(self):
        """
        Responsible for:
        - Creating the PR
        - Setting pr_obj
        - Setting pull_request_id
        """
        raise NotImplementedError

    async def _set_repo(self, use_request_branch: bool):
        self.iambic_repo.request_id = self.request_id
        self.iambic_repo.requested_by = self.requested_by
        self.iambic_repo.use_request_branch = use_request_branch
        await self.iambic_repo.set_repo()

    async def get_request_notes(self, branch_name: str):
        """
        Get the notes from the latest commit on the specified branch
        """
        await self._set_repo(use_request_branch=True)
        await aio_wrapper(
            self.iambic_repo.repo.git.fetch,
            "origin",
            "refs/notes/commits:refs/notes/commits",
        )
        branch = self.iambic_repo.repo.heads[branch_name]
        commit = branch.commit
        return await aio_wrapper(self.iambic_repo.repo.git.notes, "show", commit.hexsha)

    async def create_request(
        self,
        description: str,
        template_changes: list[IambicTemplateChange],
        request_notes: Optional[str] = None,
    ):
        await self._set_repo(use_request_branch=False)

        self.title = f"Request on behalf of {self.requested_by}"
        self.description = description
        branch_name = await self.iambic_repo.create_branch(
            self.request_id, self.requested_by, template_changes, request_notes
        )
        await self._create_request()
        return branch_name

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
        request_notes: Optional[str] = None,
        reset_branch=False,
    ):
        await self._set_repo(use_request_branch=True)
        await self.load_pr()

        if description and self.description != description:
            self.description = description
            await self._update_request()

        if template_changes:
            return await self.iambic_repo.update_branch(
                template_changes, updated_by, request_notes, reset_branch=reset_branch
            )

    async def _apply_request(self, approved_by: str):
        raise NotImplementedError

    async def apply_request(self, approved_by: Union[str, list[str]]):
        if not self.pr_obj:
            await self.load_pr()

        if self.mergeable:
            await self._apply_request(approved_by)
        elif self.mergeable and not self.merge_on_approval:
            # TODO: Return something to let user know they need to merge the PR manually
            pass
        elif not self.mergeable and not self.merged_at:
            # TODO: Mark as rejected
            pass
        elif not self.merged_at:
            raise Exception("PR can not be merged")

    async def _merge_request(self, approved_by: Union[str, list[str]]):
        raise NotImplementedError

    async def merge_request(self, approved_by: Union[str, list[str]]):
        if not self.pr_obj:
            await self.load_pr()

        if self.mergeable:
            await self._merge_request(approved_by)

    async def remove_branch(self, pull_default: bool):
        await self.iambic_repo.delete_branch()
        if pull_default:
            await self.iambic_repo.clone_or_pull_git_repo()

    async def _reject_request(self):
        """
        Responsible for:
        - Closing the PR
        """
        raise NotImplementedError

    async def reject_request(self):
        log_data = dict(
            tenant=self.tenant,
            request_id=self.request_id,
            function=f"{__name__}.{sys._getframe().f_code.co_name}",
        )
        log.debug({"message": "Rejecting request", **log_data})
        await self.load_pr()
        await self._reject_request()
        await self._set_repo(use_request_branch=False)
        await self.iambic_repo.delete_branch()

    async def get_request_details(self):
        if self.pull_request_id and not self.files:
            await self.load_pr()

        return self.dict()

    def dict(
        self,
        **kwargs,
    ) -> dict:
        required_keys_to_exclude = {
            "tenant",
            "iambic_repo",
            "pr_provider",
            "pr_obj",
        }
        if exclude := kwargs.get("exclude"):
            if not isinstance(exclude, set):
                exclude = set(exclude) if isinstance(exclude, list) else {exclude}

            exclude.update(required_keys_to_exclude)
            kwargs["exclude"] = exclude
        else:
            kwargs["exclude"] = required_keys_to_exclude

        request_dict = json.loads(json.dumps(super().dict(**kwargs)))
        request_dict["tenant"] = self.tenant.name
        request_dict["repo_name"] = self.iambic_repo.repo_name
        return request_dict


class GitHubPullRequest(BasePullRequest):
    async def get_pr_provider(self):
        if self.pr_provider:
            return self.pr_provider

        self.pr_provider = Github(
            await self.iambic_repo.get_repo_access_token()
        ).get_repo(self.iambic_repo.repo_name)
        return self.pr_provider

    async def _get_file_as_pr_file(
        self, file: File, sha: str, previous_sha: str
    ) -> PullRequestFile:
        file_path = file.filename
        previous_file_path = file.previous_filename or file_path

        if not self.merged_at and not self.closed_at:
            # Read from local file system if the request is still open
            path = os.path.join(self.iambic_repo.request_file_path, file_path)
            template_body = await self.iambic_repo.storage_handler.read_file(path, "r")

            previous_path = os.path.join(
                self.iambic_repo.default_file_path, previous_file_path
            )
            if os.path.exists(previous_path):
                previous_body = await self.iambic_repo.storage_handler.read_file(
                    previous_path, "r"
                )
            else:
                previous_body = ""

        else:
            # Otherwise, we need to resolve the relevant shas and use those
            pr_provider = await self.get_pr_provider()
            template_body = await aio_wrapper(
                pr_provider.get_contents, file_path, ref=sha
            )
            template_body = template_body.decoded_content.decode("utf-8")

            if file.status == "added":
                previous_body = ""
            else:
                previous_body = await aio_wrapper(
                    pr_provider.get_contents, previous_file_path, ref=previous_sha
                )
                previous_body = previous_body.decoded_content.decode("utf-8")

        return PullRequestFile(
            file_path=file_path,
            template_body=template_body,
            previous_body=previous_body,
            **getattr(file, "_rawData"),
        )

    async def load_pr(self):
        assert self.pull_request_id
        if not self.iambic_repo.request_id:
            await self._set_repo(False)

        pr_provider = await self.get_pr_provider()
        self.pr_obj = await aio_wrapper(pr_provider.get_pull, self.pull_request_id)
        self.pull_request_id = self.pr_obj.number
        self.pull_request_url = self.pr_obj.html_url
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
                        created_at=comment.created_at,
                    )
                )

        previous_sha = None
        if until := self.merged_at or self.closed_at:
            commit_shas = [
                commit.sha for commit in (await aio_wrapper(self.pr_obj.get_commits))
            ]
            if merge_sha := self.pr_obj.merge_commit_sha:
                commit_shas.append(merge_sha)
            previous_sha = await self.iambic_repo.get_main_sha(commit_shas, until)

        files = await aio_wrapper(self.pr_obj.get_files)
        sha = self.pr_obj.merge_commit_sha or self.pr_obj.head.sha
        self.files = list(
            await asyncio.gather(
                *[self._get_file_as_pr_file(file, sha, previous_sha) for file in files]
            )
        )

    async def sign_and_comment(self, body: str, approved_by: Union[str, list[str]]):
        loaded_private_key = serialization.load_pem_private_key(
            GITHUB_APP_APPROVE_PRIVATE_PEM_1, None
        )
        private_pem_bytes = loaded_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        if isinstance(approved_by, str):
            approved_by = [approved_by]
        payload = {
            "repo": self.iambic_repo.repo_name,
            "pr": self.pull_request_id,
            "signee": approved_by,
        }
        algorithm = "ES256"
        valid_period_in_minutes = 15
        encoded_jwt = jws_encode_with_past_time(
            payload, private_pem_bytes, algorithm, valid_period_in_minutes
        )

        # message format for approve
        # iambic approve\n
        # <whatever nice message you like>\n
        # <!--{encoded_jwt}-->
        # remember last line cannot have any newline character, the signature metadata must be on the last line

        message = f"""{body}
    ```json
    {json.dumps(payload)}
    ```
<!--{encoded_jwt}-->"""

        await self.add_comment(message)

    async def add_comment(
        self,
        body: str,
        commented_by: Optional[Union[str, list]] = None,
        original_comment_id: str = None,
    ):
        if commented_by:
            if isinstance(commented_by, str):
                commented_by = [commented_by]

            commented_by = ", ".join([f"@{user}" for user in commented_by])
            body = f"{body} on behalf of {commented_by}"
        self.pr_obj.create_issue_comment(body)

    async def update_comment(self, comment_id: int, body: str):
        raise NotImplementedError

    async def delete_comment(self, comment_id: int):
        raise NotImplementedError

    async def get_notes(self):
        raise NotImplementedError

    async def _create_request(self):
        pr_provider = await self.get_pr_provider()
        self.pr_obj = await aio_wrapper(
            pr_provider.create_pull,
            title=self.title,
            body=self.description,
            head=self.iambic_repo.request_branch_name,
            base=self.iambic_repo.default_branch_name,
        )
        self.pull_request_id = self.pr_obj.number
        self.pull_request_url = self.pr_obj.html_url

    async def _update_request(self):
        await aio_wrapper(
            self.pr_obj.edit,
            body=self.description,
        )
        self.pull_request_id = self.pr_obj.number
        self.pull_request_url = self.pr_obj.html_url

    async def _merge_request(self, approved_by: Union[str, list[str]]):
        await self.add_comment("iambic apply", approved_by)

    async def _apply_request(self, approved_by: Union[str, list[str]]):
        await self.sign_and_comment("iambic approve", approved_by)

    async def _reject_request(self):
        await aio_wrapper(self.pr_obj.edit, state="closed")


class Request(SoftDeleteMixin, Base):
    __tablename__ = "request"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_name = Column(String)
    justification = Column(String, default="N/A")
    pull_request_id = Column(Integer)
    pull_request_url = Column(String)
    tenant_id = Column(Integer, ForeignKey("tenant.id"))
    status = Column(RequestStatus, default="Pending")
    request_method = Column(String, nullable=True)
    slack_username = Column(String, nullable=True)
    slack_email = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    request_notes = Column(String, nullable=True)
    slack_channel_id = Column(String, nullable=True)
    slack_message_id = Column(String, nullable=True)
    branch_name = Column(String, nullable=True)

    allowed_approvers = Column(ARRAY(String), default=dict)
    approved_by = Column(ARRAY(String), default=dict)
    rejected_by = Column(String, nullable=True)

    tenant = relationship("Tenant")

    comments = relationship(
        "RequestComment",
        back_populates="request",
        cascade="all, delete-orphan",
        uselist=True,
        order_by="RequestComment.created_at",
    )

    __table_args__ = (
        Index("request_tenant_created_at_idx", "tenant_id", "deleted", "created_at"),
        Index(
            "request_tenant_with_status_created_at_idx",
            "tenant_id",
            "status",
            "deleted",
            "created_at",
        ),
        Index(
            "request_created_by_created_at_idx",
            "tenant_id",
            "deleted",
            "created_by",
            "created_at",
        ),
        Index(
            "request_created_by_with_status_created_at_idx",
            "tenant_id",
            "status",
            "deleted",
            "created_by",
            "created_at",
        ),
        Index("request_pr_idx", "tenant_id", "pull_request_id", "repo_name"),
    )

    def dict(self):
        response = {
            "id": str(self.id),
            "repo_name": self.repo_name,
            "pull_request_id": self.pull_request_id,
            "status": self.status
            if isinstance(self.status, str)
            else self.status.value,
            "allowed_approvers": self.allowed_approvers,
            "created_at": self.created_at.timestamp(),
            "created_by": self.created_by,
        }
        for conditional_key in (
            "approved_by",
            "rejected_by",
            "pull_request_url",
            "updated_at",
            "updated_by",
        ):
            if val := getattr(self, conditional_key):
                response[conditional_key] = val

        return response

    async def write(self):
        async with ASYNC_PG_SESSION() as session:
            async with session.begin():
                session.add(self)
                await session.commit()
            return True


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
