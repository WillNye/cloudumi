from common.handlers.base import BaseAdminHandler
from common.models import WebResponse
from common.role_access.models import RoleAccess
from common.tenants.models import Tenant
from common.users.models import User


class ManageRoleAccessHandler(BaseAdminHandler):
    async def get(self):
        username = self.get_current_user()
        tenant = Tenant.get_by_name(self.ctx.tenant)
        user = User.get_by_username(self.ctx.tenant, username)
        access_roles = await RoleAccess.list_by_user(tenant=tenant, user=user)
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"access_roles": access_roles},
            ).dict(exclude_unset=True, exclude_none=True)
        )
