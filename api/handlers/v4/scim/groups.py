import re

import tornado.escape

import common.lib.noq_json as json
from common.groups.models import Group
from common.handlers.base import ScimAuthHandler
from common.models import WebResponse
from common.users.models import User


class ScimV2GroupsHandler(ScimAuthHandler):
    """Handler for SCIM v2 Groups API endpoints."""

    async def get(self):
        """Get a list of groups."""
        offset = int(self.get_argument("startIndex", 0))
        all_groups = []
        filters = {}

        count = int(self.get_argument("count", 0))

        if "filter" in self.request.arguments:
            request_filter = self.get_argument("filter", "")
            match = None
            if request_filter:
                match = re.match(r'(\w+) eq "([^"]*)"', request_filter)
                (search_key_name, search_value) = match.groups()
                filters[f"{search_key_name}__eq"] = search_value

        groups = await Group.get_all(
            self.ctx.tenant, get_users=True, offset=offset, count=count, filters=filters
        )

        for group in groups:
            all_groups.append(await group.serialize_for_scim())
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(all_groups))

    async def post(self):
        """Create a new group."""
        body = tornado.escape.json_decode(self.request.body)
        displayName = body["displayName"]
        members = body.get("members", [])
        users = []
        for member in members:
            user = await User.get_by_id(self.ctx.tenant, member["value"])
            if not user:
                self.set_status(404)
                self.write(
                    WebResponse(
                        success="error",
                        status_code=404,
                        data={"message": "User not found"},
                    ).dict(exclude_unset=True, exclude_none=True)
                )
                return
            users.append(user)

        try:
            group = Group(name=displayName, tenant=self.ctx.tenant, users=users)
            await group.write()
            group = await Group.get_by_id(self.ctx.tenant, group.id, get_users=True)
            serialized_group = await group.serialize_for_scim()
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(serialized_group))
        except Exception:
            raise


class ScimV2GroupHandler(ScimAuthHandler):
    """Handler for SCIM v2 Group API endpoints."""

    async def get(self, group_id):
        """Get a group by ID."""
        group = await Group.get_by_id(self.ctx.tenant, group_id)
        if group:
            serialized_group = await group.serialize_for_scim()
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(serialized_group))
        else:
            self.set_status(404)
            self.write(
                WebResponse(
                    success="error",
                    status_code=404,
                    data={"message": "Group not found"},
                ).dict(exclude_unset=True, exclude_none=True)
            )

    async def update(self, group_id):
        """Update a group by ID."""
        group = await Group.get_by_id(self.ctx.tenant, group_id, get_users=True)
        if not group:
            self.set_status(404)
            self.write(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": "Group not found",
                    "status": 404,
                }
            )
            raise tornado.web.Finish()

        body = tornado.escape.json_decode(self.request.body)
        displayName = body["displayName"]
        group.name == displayName
        members = body.get("members")
        if not members:
            members = body["Operations"][0]["value"]

            if body["Operations"][0]["op"] == "replace":
                raise tornado.web.Finish()

        users = []
        for member in members:
            user = await User.get_by_id(self.ctx.tenant, member["value"])
            if not user:
                self.set_status(404)
                self.write(
                    {
                        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                        "detail": "User not found",
                        "status": 404,
                    }
                )
                raise tornado.web.Finish()
            users.append(user)

        group.users = users
        await group.write()
        serialized_group = await group.serialize_for_scim()
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(serialized_group))

    async def put(self, group_id):
        await self.update(group_id)

    async def patch(self, group_id):
        await self.update(group_id)

    async def delete(self, group_id):
        """Delete a group by ID."""
        group = await Group.get_by_id(self.ctx.tenant, group_id)
        if not group:
            self.set_status(404)
            self.write(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": "Group not found",
                    "status": 404,
                }
            )
            raise tornado.web.Finish()
        await group.delete()
