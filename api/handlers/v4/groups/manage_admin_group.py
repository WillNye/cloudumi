from itertools import compress

import tornado.escape
import tornado.gen
import tornado.web
from email_validator import validate_email

from api.handlers.model_handlers import ConfigurationCrudHandler
from common.handlers.base import BaseAdminHandler
from common.lib.asyncio import aio_wrapper
from common.lib.dictutils import get_in, set_in
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.pydantic import BaseModel
from common.lib.yaml import yaml
from common.models import Status2, WebResponse


class ManageGroupAdminHandler(BaseAdminHandler):
    """Handler for /api/v4/group_admin/?"""

    async def validate_groups(self):
        """Validate and return groups"""
        data = tornado.escape.json_decode(self.request.body)
        groups: list[str] = data.get("groups")

        if any([not validate_email(group) for group in groups]):
            self.set_status(403)
            self.write(
                WebResponse(
                    status=Status2.error,
                    status_code=403,
                    reason="Invalid email address",
                    data={
                        "message": f"{', '.join(compress(groups, [not validate_email(group) for group in groups]))}"
                    },
                ).dict(exclude_unset=True, exclude_none=True)
            )
            raise tornado.web.Finish()

        return groups

    async def get(self):
        """Retrieve groups that can admin current tenant"""
        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        return self.write(
            WebResponse(
                status=Status2.success,
                status_code=200,
                data=get_in(dynamic_config, "groups.can_admin"),
                reason=None,
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def put(self):
        """Add groups that can admin current tenant"""
        groups = await self.validate_groups()

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        current_groups: list[str] = list(get_in(dynamic_config, "groups.can_admin"))  # type: ignore

        set_in(
            dynamic_config, "groups.can_admin", list(set([*current_groups, *groups]))
        )

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )

        return self.write(
            WebResponse(
                status=Status2.success, status_code=201, reason=None, data={}
            ).dict(exclude_unset=True, exclude_none=True)
        )

    async def delete(self):
        """Remove groups that can admin current tenant"""
        groups = await self.validate_groups()

        ddb = RestrictedDynamoHandler()
        dynamic_config = await aio_wrapper(
            ddb.get_static_config_for_tenant_sync,
            self.ctx.tenant,
            return_format="dict",
            filter_secrets=True,
        )

        current_groups: set[str] = set(list(get_in(dynamic_config, "groups.can_admin")))  # type: ignore
        difference = list(current_groups.difference(groups))

        if len(difference) < 1:
            raise ValueError("You must at least have one admin group")

        set_in(dynamic_config, "groups.can_admin", difference)

        await ddb.update_static_config_for_tenant(
            yaml.dump(dynamic_config),
            self.user,
            self.ctx.tenant,
        )

        return self.write(
            WebResponse(
                status=Status2.success, status_code=201, reason=None, data={}
            ).dict(exclude_unset=True, exclude_none=True)
        )


class GroupsCanAdminRequest(BaseModel):
    can_admin: list[str]


class GroupsCanAdminConfigurationCrudHandler(ConfigurationCrudHandler):
    _model_class = GroupsCanAdminRequest
    _config_key = "groups"
