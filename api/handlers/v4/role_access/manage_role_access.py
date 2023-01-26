import tornado.escape
import tornado.gen
import tornado.web
from email_validator import validate_email

from common.handlers.base import BaseAdminHandler
from common.identity.models import IdentityRole
from common.models import WebResponse
from common.role_access.models import RoleAccess
from common.users.models import User


class ManageRoleAccessHandler(BaseAdminHandler):
    async def get(self):
        username = self.get_current_user()
        user = User.get_by_username(self.ctx.tenant, username)
        access_roles = await query_role_access(self.ctx.tenant, user=user)
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"access_roles": access_roles},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        username = self.get_current_user()
        user = User.get_by_username(self.ctx.tenant, username)
        role_arn = data.get("role_arn")
        if not role_arn:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Role ARN is required"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        role_access = await RoleAccess.get_by_user_and_role_arn(
            self.ctx.tenant, user, role_arn
        )
        if not role_access:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Role access does not exist"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        await role_access.delete()
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Role access deleted successfully"},
            ).dict(exclude_unset=True, exclude_none=True)
        )
