import tornado.escape
import tornado.gen
import tornado.web

from common.group_memberships.models import GroupMembership
from common.groups.models import Group
from common.handlers.base import BaseAdminHandler
from common.models import WebResponse
from common.users.models import User


class ManageGroupMembershipsHandler(BaseAdminHandler):
    async def post(self):
        # Get the username and password from the request body
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
                membership = await GroupMembership.create(user, group)
                if not membership:
                    messages.append(
                        {
                            "message": "Unable to add user to group. Membership already exists",
                            "user_name": user_name,
                            "group_name": group_name,
                        }
                    )
                    continue
                messages.append(
                    {
                        "message": "User added to group",
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
