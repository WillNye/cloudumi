import tornado.escape
import tornado.gen
import tornado.web
from email_validator import validate_email

from common.groups.models import Group
from common.handlers.base import BaseAdminHandler
from common.models import WebResponse


class ManageGroupsHandler(BaseAdminHandler):
    async def get(self):
        all_groups = await Group.get_all(self.ctx.db_tenant, get_users=True)
        groups = []
        for group in all_groups:
            users = [user.email for user in group.users]
            groups.append(
                {
                    "id": str(group.id),
                    "name": group.name,
                    "users": users,
                }
            )
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"groups": groups},
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        group_name = data.get("name")
        group_description = data.get("description")
        group_email = data.get("email")
        if group_email and not validate_email(group_email):
            self.set_status(403)
            self.write(
                WebResponse(
                    success="error",
                    status_code=403,
                    data={"message": "Invalid email address"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        existing_group = await Group.get_by_name(self.ctx.db_tenant, group_name)
        if existing_group:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Group name already taken"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            return

        created_group = await Group.create(
            tenant=self.ctx.db_tenant,
            name=group_name,
            email=group_email,
            description=group_description,
        )

        self.write(
            WebResponse(
                success="success",
                message="Successfully created group",
                status_code=200,
                data={
                    "id": created_group.id,
                    "name": created_group.name,
                    "description": created_group.description,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def put(self):
        data = tornado.escape.json_decode(self.request.body)

        # Get the user id and security action from the request
        group_id = data.get("id")
        group_name = data.get("name")
        group_description = data.get("description")
        group_email = data.get("email")

        db_group = await Group.get_by_id(self.ctx.db_tenant, group_id)

        if not db_group:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Group does not exist"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        new_db_group = await db_group.update(
            name=group_name,
            description=group_description,
            email=group_email,
            # updated_by=self.user,
            # updated_at=datetime.utcnow()
        )
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={
                    "id": new_db_group.id,
                    "name": new_db_group.name,
                    "description": new_db_group.description,
                    "email": new_db_group.email,
                },
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        data = tornado.escape.json_decode(self.request.body)
        group_name = data.get("name")

        db_group = await Group.get_by_name(self.ctx.db_tenant, group_name)
        if not db_group:
            self.set_status(400)
            self.write(
                WebResponse(
                    success="error",
                    status_code=400,
                    data={"message": "Group does not exist"},
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        await db_group.delete()
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data={"message": "Group deleted successfully"},
            ).dict(exclude_unset=True, exclude_none=True)
        )
