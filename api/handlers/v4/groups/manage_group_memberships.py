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
        check_deleted = data.get("check_deleted", False)
        group_names = data.get("groups")
        user_names = data.get("users")
        messages = []

        if check_deleted:
            # if check_deleted is true, delete any memberships
            # that exist for the user and group and are not in the list of groups to add
            for user_name in user_names:
                user = await User.get_by_username(self.ctx.db_tenant, user_name)
                if not user:
                    continue
                memberships = await GroupMembership.get_by_user(user)
                for membership in memberships:
                    group = await Group.get_by_id(
                        self.ctx.db_tenant, membership.group_id
                    )
                    if not group:
                        continue
                    # if group is not in the list, delete the membership
                    if group.name not in group_names:
                        deleted = await membership.delete()
                        if not deleted:
                            messages.append(
                                {
                                    "message": "Unable to remove Membership.",
                                    "user_name": user_name,
                                    "group_name": group.name,
                                }
                            )
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
                memberships = await GroupMembership.get_by_group(group)
                for membership in memberships:
                    user = await User.get_by_id(self.ctx.db_tenant, membership.user_id)
                    if not user:
                        continue
                    # if user is not in the list delete the membership
                    if user.username not in group_names:
                        deleted = await membership.delete()
                        if not deleted:
                            messages.append(
                                {
                                    "message": "Unable to remove Membership.",
                                    "user_name": user.username,
                                    "group_name": group.name,
                                }
                            )

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
