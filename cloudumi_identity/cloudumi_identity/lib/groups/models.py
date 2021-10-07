from typing import Dict, Set

from pydantic import BaseModel

# Reference: https://www.guidodiepen.nl/2019/02/implementing-a-simple-plugin-framework-in-python/


class Group(BaseModel):
    name: str
    domain: str
    group_id: str
    friendly_name: str
    description: str
    settings: str
    aliases: str
    members: str
    attributes: str
    automated_group: str


class User(BaseModel):
    username: str
    domain: str
    fullname: str
    status: str
    created: str
    updated: str
    groups: List[str]
    background_check_status: str


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
    users: List[User]
    groups: List[Group]
    requester: User
    justification: Dict[str, str]
    expires: Optional[int] = None
    status: GroupRequestStatus
    last_updated: List[LastUpdated]
    last_updated_time: int
    last_updated_by: User


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
