from typing import Optional

import tornado.escape
import tornado.gen
import tornado.web
from pydantic import BaseModel, Field, validator

from common.group_memberships.models import GroupMembership
from common.groups.models import Group
from common.handlers.base import BaseAdminHandler
from common.models import WebResponse
from common.users.models import User


class MembershipData(BaseModel):
    groups: list[str] = Field(...)
    users: list[str] = Field(...)
    check_deleted: Optional[bool] = False

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
                    success="failed",
                    status_code=400,
                    errors=[{"message": f"Invalid input data: {e}"}],
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        messages = []

        if data.check_deleted:
            messages += await self.remove_memberships(data)

        messages += await self.add_memberships(data)

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": messages},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def remove_memberships(self, data):
        messages = []
        for user_name in data.users:
            user = await User.get_by_username(self.ctx.db_tenant, user_name)
            if not user:
                continue
            memberships = await GroupMembership.get_by_user(user)
            for membership in memberships:
                group = await Group.get_by_id(self.ctx.db_tenant, membership.group_id)
                if not group:
                    continue
                if not group.managed_by == "MANUAL":
                    messages.append(
                        {
                            "type": "error",
                            "message": "Group is managed by an external system. Cannot add users to group.",
                            "group_name": group.name,
                        }
                    )
                    continue
                if group.name not in data.groups:
                    deleted = await membership.delete()
                    if not deleted:
                        messages.append(
                            {
                                "type": "error",
                                "message": "Unable to remove Membership.",
                                "user_name": user_name,
                                "group_name": group.name,
                            }
                        )
                        continue
                    messages.append(
                        {
                            "type": "success",
                            "message": "Membership removed successfully.",
                            "user_name": user_name,
                            "group_name": group.name,
                        }
                    )

        return messages

    async def add_memberships(self, data):
        messages = []
        for group_name in data.groups:
            group = await Group.get_by_name(self.ctx.db_tenant, group_name)
            if not group:
                messages.append(
                    {
                        "type": "error",
                        "message": "Invalid group",
                        "group_name": group_name,
                    }
                )
                continue
            if not group.managed_by == "MANUAL":
                messages.append(
                    {
                        "type": "error",
                        "message": "Group is managed by an external system. Cannot add users to group.",
                        "group_name": group_name,
                    }
                )
                continue
            for user_name in data.users:
                user = await User.get_by_username(self.ctx.db_tenant, user_name)
                if not user:
                    messages.append(
                        {
                            "type": "error",
                            "message": "Invalid user",
                            "user_name": user_name,
                        }
                    )
                    continue
                membership = await GroupMembership.create(user, group)
                if not membership:
                    messages.append(
                        {
                            "type": "error",
                            "message": "Unable to add user to group. Membership already exists",
                            "user_name": user_name,
                            "group_name": group_name,
                        }
                    )
                    continue
                messages.append(
                    {
                        "type": "success",
                        "message": "User added to group",
                        "user_name": user_name,
                        "group_name": group_name,
                    }
                )
        return messages

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        group_names = data.get("groups")
        user_names = data.get("users")
        messages = []
        for group_name in group_names:
            group = await Group.get_by_name(self.ctx.db_tenant, group_name)
            if not group:
                messages.append(
                    {
                        "message": "Invalid group",
                        "group_name": group_name,
                    }
                )
                continue
            for user_name in user_names:
                user = await User.get_by_username(self.ctx.db_tenant, user_name)
                if not user:
                    messages.append(
                        {
                            "message": "Invalid user",
                            "user_name": user_name,
                        }
                    )
                    continue
                membership = await GroupMembership.get(user, group)
                if not membership:
                    messages.append(
                        {
                            "message": "Group membership doesn't exist",
                            "user_name": user_name,
                            "group_name": group_name,
                        }
                    )
                    continue
                deleted = await membership.delete()
                if not deleted:
                    messages.append(
                        {
                            "message": "Unable to delete group membership",
                            "user_name": user_name,
                            "group_name": group_name,
                        }
                    )
                    continue
                messages.append(
                    {
                        "message": "Group membership deleted",
                        "user_name": user_name,
                        "group_name": group_name,
                    }
                )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": messages},
            ).dict(exclude_unset=True, exclude_none=True)
        )
