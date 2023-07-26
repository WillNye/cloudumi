from api.handlers.model_handlers import MultiItemsDDBConfigurationCrudHandler
from common.lib.pydantic import BaseModel


class GroupsCanAdminRequest(BaseModel):
    groups: list[str]


class GroupsCanAdminConfigurationCrudHandler(MultiItemsDDBConfigurationCrudHandler):
    """Handler for /api/v4/group_admin/?"""

    _model_class = GroupsCanAdminRequest
    _config_key = "groups.can_admin"
    _request_list_key = "groups"

    async def _validate_body(self, groups: list[str]):
        # Some providers do not use email as group name
        # if any([not validate_email(group) for group in groups]):
        #     self.set_status(403)
        #     self.write(
        #         WebResponse(
        #             status=Status2.error,
        #             status_code=403,
        #             reason="Invalid email address",
        #             data={
        #                 "message": f"{', '.join(compress(groups, [not validate_email(group) for group in groups]))}"
        #             },
        #         ).dict(exclude_unset=True, exclude_none=True)
        #     )
        #     raise tornado.web.Finish()
        return True

    async def _validate_delete(self, **kwargs):
        if len(kwargs["difference"]) < 1:
            raise ValueError("You must at least have one admin group")

        return True
