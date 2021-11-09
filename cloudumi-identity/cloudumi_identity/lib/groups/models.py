from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, constr

from cloudumi_common.lib.pydantic import BaseModel

# Reference: https://www.guidodiepen.nl/2019/02/implementing-a-simple-plugin-framework-in-python/


class IdentityProvider(BaseModel):
    name: str


class OktaIdentityProvider(IdentityProvider):
    idp_type: constr(regex=r"okta")
    org_url: str
    api_token: str


class UserStatus(Enum):
    active = "active"
    provisioned = "provisioned"
    deprovisioned = "deprovisioned"


class User(BaseModel):
    idp_name: str
    username: str
    host: str
    user_id: str
    domain: Optional[str]
    fullname: Optional[str]
    status: Optional[UserStatus]
    created: Optional[str]
    updated: Optional[str]
    groups: Optional[List[str]]
    background_check_status: Optional[bool]
    extra: Any = Field(None, description=("Extra attributes to store"))


class GroupAttributes(BaseModel):
    requestable: bool = Field(
        False, description="Whether end-users can request access to group"
    )
    manager_approval_required: bool = Field(
        False, description="Whether a manager needs to approve access to the group"
    )
    approval_chain: List[Union[User, str]] = Field(
        [],
        description="A list of users or groups that need to approve access to the group",
    )
    self_approval_groups: List[str] = Field(
        [],
        description=(
            "If the user is a member of a self-approval group, their request to the group "
            "will be automatically approved"
        ),
    )
    allow_bulk_add_and_remove: bool = Field(
        True,
        description=(
            "Controls whether administrators can automatically approve access to the group"
        ),
    )
    background_check_required: bool = Field(
        False,
        description=("Whether a background check is required to be added to the group"),
    )
    allow_contractors: bool = Field(
        False,
        description=("Whether contractors are allowed to be members of the group"),
    )
    allow_third_party: bool = Field(
        False,
        description=(
            "Whether third-party users are allowed to be a member of the group"
        ),
    )
    emails_to_notify_on_new_members: List[str] = Field(
        [],
        description=(
            "A list of e-mail addresses to notify when new users are added to the group."
        ),
    )


class Group(BaseModel):
    host: str = Field(..., description="Host/Tenant associated with the group")
    name: str = Field(..., description="Name of the group")
    owner: Optional[str] = Field(None, description="Owner of the group")
    idp_name: str = Field(
        ...,
        description="Name of the host's identity provider that's associated with the group",
    )
    group_id: str = Field(
        ..., description="Unique Group ID for the group. Usually it's {idp-name}-{name}"
    )
    description: Optional[str] = Field(None, description="Description of the group")
    attributes: GroupAttributes = Field(
        ...,
        description=(
            "Protected attributes that tell us whether the group is requester, where approvals should be routed, etc."
        ),
    )
    extra: Any = Field(None, description=("Extra attributes to store"))
    members: Optional[List[User]] = Field(None, description="Users in the group")


class ActionStatus(Enum):
    success = "success"
    error = "error"


class ActionResponse(BaseModel):
    status: Optional[ActionStatus] = None
    errors: Optional[List[str]] = None
    data: Any = None


class GroupRequestStatus(Enum):
    pending = "pending"
    approved = "approved"
    cancelled = "cancelled"
    rejected = "rejected"


class LastUpdated(BaseModel):
    user: User
    time: int
    comment: str


class GroupRequest(BaseModel):
    request_id: str
    request_url: str
    host: str
    users: List[User]
    groups: List[Group]
    requester: User
    justification: str
    expires: Optional[int] = None
    status: GroupRequestStatus
    created_time: int
    last_updated: List[LastUpdated]
    last_updated_time: int
    last_updated_by: User


class GroupRequests(BaseModel):
    requests: List[GroupRequest]


class GroupRequestsTable(BaseModel):
    User: str
    Group: str
    Requester: str
    Justification: str
    Expires: Optional[str]
    Status: str
    Last_Updated: str


# TODO: Justification might be multiple fields. Should be a struct. Should allow RegEx validation
# TODO: Support Temporary Requests
class GroupManagementPlugin:
    def __init__(self):
        pass

    async def create_group_request(
        self,
        users: List[User],
        groups: List[Group],
        requester: User,
        justification: Dict[str, str],
        expires: Optional[int] = None,
    ) -> ActionResponse:
        # Should return a request object
        raise NotImplementedError

    async def list_all_users(self) -> List[User]:
        raise NotImplementedError

    async def list_all_groups(self) -> List[Group]:
        raise NotImplementedError

    async def add_user_to_group(
        self, user: User, group: Group, requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def get_group(self, group_name: str):
        raise NotImplementedError

    async def add_user_to_groups(
        self, user: User, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def remove_user_from_group(
        self, user: User, group: Group, requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def remove_user_from_groups(
        self, user: User, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def list_group_members(self, group: Group, requester: User) -> ActionResponse:
        raise NotImplementedError

    async def list_groups_members(
        self, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def get_user_group_memberships(self, user: User) -> ActionResponse:
        raise NotImplementedError

    async def get_users_group_memberships(self, user: List[User]) -> ActionResponse:
        raise NotImplementedError

    async def list_group_users(self, group: Group):
        raise NotImplementedError

    async def create_group(self, group: Group):
        raise NotImplementedError

    async def add_group_target_to_role(
        self, user_id: str, user_role_id: str, group_id: str
    ):
        raise NotImplementedError

    async def create_user(self, user: User):
        raise NotImplementedError

    async def activate_user(self, user_id: str):
        raise NotImplementedError

    async def suspend_user(self, user_id: str):
        raise NotImplementedError

    async def unsuspend_user(self, user_id: str):
        raise NotImplementedError

    async def assign_role_to_user(self, user_id: str, req):
        raise NotImplementedError

    async def get_user(self, user_id: str):
        raise NotImplementedError

    async def deactivate_or_delete_user(self, user_id: str):
        raise NotImplementedError

    async def assign_role_to_group(self, group: Group, req):
        raise NotImplementedError

    async def list_group_assigned_roles(self, group: Group):
        raise NotImplementedError

    async def remove_role_from_group(self, group: Group):
        raise NotImplementedError

    async def create_application(self, req):
        raise NotImplementedError

    async def create_application_group_assignment(
        self, app, group: Group, app_group_assignment
    ):
        raise NotImplementedError

    async def list_assigned_applications_for_group(self, group: Group):
        raise NotImplementedError

    async def deactivate_application(self, app):
        raise NotImplementedError

    async def delete_application(self, app):
        raise NotImplementedError

    async def delete_group(self, group: Group):
        raise NotImplementedError
