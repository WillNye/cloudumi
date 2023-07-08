from itertools import compress, product

import tornado.escape
import tornado.gen
import tornado.web
from pydantic import BaseModel, Field, validator

from common.group_memberships.models import GroupMembership
from common.groups.models import Group
from common.handlers.base import BaseAdminHandler
from common.models import Status2, WebResponse
from common.pg_core.utils import bulk_add, bulk_delete
from common.users.models import User


class MembershipData(BaseModel):
    groups: list[str] = Field(...)
    users: list[str] = Field(...)

    @validator("groups", "users", pre=True, each_item=True)
    def escape_injection(cls, v):
        return tornado.escape.xhtml_escape(v)


class ManageGroupMembershipsHandler(BaseAdminHandler):
    async def post(self):
        try:
            data = MembershipData.parse_raw(self.request.body)
        except ValueError as e:
            self.write(
                WebResponse(
                    status=Status2.error,
                    status_code=400,
                    reason="Invalid input data",
                    errors=[{"message": f"Invalid input data: {e}"}],
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        messages = await self.add_memberships(data)

        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
                data={"message": messages},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        try:
            data = MembershipData.parse_raw(self.request.body)
        except ValueError as e:
            self.write(
                WebResponse(
                    status=Status2.error,
                    status_code=400,
                    reason="Invalid input data",
                    errors=[{"message": f"Invalid input data: {e}"}],
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        messages = await self.remove_memberships(data)
        self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                reason=None,
                data={"message": messages},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def add_memberships(self, data: MembershipData):
        messages = []

        users = await self._get_users(data, messages)
        groups = await self._get_groups(data, messages)

        memberships = []

        # TODO: make it in parallel
        # Create group memberships for each combination of valid user and group
        for user, group in product(users, groups):
            exists = await GroupMembership.exists_by_group_and_user(user, group)
            if exists:
                messages.append(
                    {
                        "type": "error",
                        "message": f"Unable to add user {user.username} to group {group.name}. Membership already exists",
                        "user_name": user.username,
                        "group_name": group.name,
                    }
                )
                continue

            memberships.append(GroupMembership(group_id=group.id, user_id=user.id))

        # TODO: we should execute the update, although we have errors? len(messages)
        if memberships:
            await bulk_add(memberships)
            messages.append(
                {
                    "type": "success",
                    "message": "Memberships created successfully.",
                }
            )

        return messages

    async def remove_memberships(self, data: MembershipData):
        messages = []

        users = await self._get_users(data, messages)
        groups = await self._get_groups(data, messages)

        memberships = []

        # TODO: make it in parallel
        # Remove group memberships for each combination of valid user and group
        for user, group in product(users, groups):
            membership = await GroupMembership.get_by_user_and_group(user, group)
            if not membership:
                messages.append(
                    {
                        "type": "error",
                        "message": f"Unable to remove Membership between user {user.username} and group {group.name}.",
                        "user_name": user.username,
                        "group_name": group.name,
                    }
                )
                continue

            memberships.append(membership)

        if memberships:
            await bulk_delete(memberships)
            messages.append(
                {
                    "type": "success",
                    "message": "Memberships removed successfully.",
                }
            )

        return messages

    async def _get_groups(self, data, messages):
        """Filter out invalid groups and collect error messages"""
        groups = await Group.get_by_names(self.ctx.db_tenant, data.groups)

        if len(groups) != len(data.groups):
            group_names = [group.name for group in groups]
            for group_name in data.groups:
                if group_name not in group_names:
                    messages.append(
                        {
                            "type": "error",
                            "message": "Invalid group {group_name}",
                            "group_name": group_name,
                        }
                    )
                    continue

        groups = list(
            compress(
                groups,
                [
                    validate_manual(group, messages, f"Group {group.name}")
                    for group in groups
                ],
            )
        )

        return groups

    async def _get_users(self, data, messages):
        """Filter out invalid users and collect error messages"""
        users = await User.get_by_usernames(self.ctx.db_tenant, data.users)
        users = list(
            compress(
                users,
                [
                    validate_manual(user, messages, f"User {user.username}")
                    for user in users
                ],
            )
        )

        if len(users) != len(data.users):
            usernames = [user.username for user in users]
            for username in data.users:
                if username not in usernames:
                    messages.append(
                        {
                            "type": "error",
                            "message": "Invalid user {user_name}",
                            "username": username,
                        }
                    )
                    continue

        return users


def validate_manual(item: Group | User, messages, name: str):
    """Validate that the item is not managed by an external system"""
    if item.managed_by is not "MANUAL":  # noqa: F632
        messages.append(
            {
                "type": "error",
                "message": "{name} is managed by an external system. Cannot add users to group.",
                "attr": name,
            }
        )
        return False
    return True
