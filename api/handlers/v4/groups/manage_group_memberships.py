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
        for group_name in group_names:
            group = await Group.get_by_name(self.ctx.tenant, group_name)
            if not group:
                self.set_status(403)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=403,
                        data={"message": f"Invalid group name: {group_name}"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            for user_name in user_names:
                user = await User.get_by_username(self.ctx.tenant, user_name)
                if not user:
                    self.set_status(403)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={"message": f"Invalid user name: {user_name}"},
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                await GroupMembership.create(user, group)

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Users added to groups"},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        group_names = data.get("groups")
        user_names = data.get("users")
        for group_name in group_names:
            group = await Group.get_by_name(self.ctx.tenant, group_name)
            if not group:
                self.set_status(403)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=403,
                        data={"message": f"Invalid group name: {group_name}"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                raise tornado.web.Finish()
            for user_name in user_names:
                user = await User.get_by_username(self.ctx.tenant, user_name)
                if not user:
                    self.set_status(403)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={"message": f"Invalid user name: {user_name}"},
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                membership = await GroupMembership.get(user, group)
                if not membership:
                    self.set_status(403)
                    self.write(
                        WebResponse(
                            success="error",
                            status_code=403,
                            data={
                                "message": f"User {user_name} is not a member of group {group_name}"
                            },
                        ).dict(exclude_unset=True, exclude_none=True)
                    )
                    raise tornado.web.Finish()
                await GroupMembership.delete(membership)

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Users removed from groups"},
            ).dict(exclude_unset=True, exclude_none=True)
        )
