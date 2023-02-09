import re

import tornado.escape

import common.lib.noq_json as json
from common.group_memberships.models import GroupMembership
from common.groups.models import Group
from common.handlers.base import ScimAuthHandler
from common.lib.password import generate_random_password
from common.users.models import User


class ScimV2UsersHandler(ScimAuthHandler):
    """Handler for SCIM v2 Users API endpoints."""

    async def get(self):
        """Get a list of users."""
        offset = int(self.get_argument("startIndex", 0))
        all_users = []
        filters = {}

        count = int(self.get_argument("count", 0))

        if "filter" in self.request.arguments:
            request_filter = self.get_argument("filter", "")
            match = None
            if request_filter:
                match = re.match(r'(\w+) eq "([^"]*)"', request_filter)
                (search_key_name, search_value) = match.groups()
                if search_key_name == "userName":
                    search_key_name = "username"
                filters[f"{search_key_name}__eq"] = search_value

        users = await User.get_all(
            self.ctx.tenant,
            get_groups=True,
            offset=offset,
            count=count,
            filters=filters,
        )

        for user in users:
            all_users.append(await user.serialize_for_scim())
        self.set_header("Content-Type", "application/json")
        self.write(
            json.dumps(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
                    "totalResults": len(all_users),
                    "startIndex": offset,
                    "itemsPerPage": count,
                    "Resources": all_users,
                }
            )
        )

    async def post(self):
        """Create a new user."""
        body = tornado.escape.json_decode(self.request.body)
        active = body.get("active")
        username = body.get("userName")
        display_name = body.get("displayName")
        emails = body.get("emails")
        external_id = body.get("externalId")
        groups = body.get("groups")
        locale = body.get("locale")
        given_name = body.get("name", {}).get("givenName")
        middle_name = body.get("name", {}).get("middleName")
        family_name = body.get("name", {}).get("familyName")
        password = body.get("password")
        if not password:
            password = await generate_random_password()

        existing_user = await User.get_by_username(self.ctx.tenant, username)

        if existing_user:
            self.set_status(409)
            self.write(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": "User already exists in the database.",
                    "status": 409,
                }
            )
            raise tornado.web.Finish()

        user = User(
            active=active,
            tenant=self.ctx.tenant,
            display_name=display_name,
            email_primary=emails[0]["primary"],
            email=emails[0]["value"],
            email_type=emails[0]["type"],
            external_id=external_id,
            locale=locale,
            given_name=given_name,
            middle_name=middle_name,
            family_name=family_name,
            password_hash=await User.generate_password_hash(password),
            username=username,
            managed_by="SCIM",
        )
        await user.write()

        if groups:
            for group in groups:
                existing_group = await Group.get_by_id(self.ctx.tenant, group["value"])
                if existing_group:
                    await GroupMembership.create(user, existing_group)
                else:
                    new_group = Group(
                        name=group["displayName"],
                        tenant=self.ctx.tenant,
                    )
                    await new_group.write()
                    await GroupMembership.create(user, new_group)
        user = await User.get_by_username(self.ctx.tenant, username, get_groups=True)
        new_user = await user.serialize_for_scim()
        self.set_status(201)
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(new_user))


class ScimV2UserHandler(ScimAuthHandler):
    """Handler for SCIM v2 User API endpoints."""

    async def get(self, user_id):
        user = await User.get_by_id(self.ctx.tenant, user_id, get_groups=True)
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
        scim_user = await user.serialize_for_scim()
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(scim_user))

    async def post(self, user_id):
        user = await User.get_by_id(self.ctx.tenant, user_id)
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
        body = tornado.escape.json_decode(self.request.body)
        user.active = body.get("active")
        user.username = body.get("userName")
        user.display_name = body.get("displayName")
        emails = body.get("emails")
        user.external_id = body.get("externalId")
        user.locale = body.get("locale")
        user.given_name = body.get("name", {}).get("givenName")
        user.middle_name = body.get("name", {}).get("middleName")
        user.family_name = body.get("name", {}).get("familyName")
        user.password = body.get("password")
        user.schemas = body.get("schemas")
        user.managed_by = "SCIM"
        if emails and len(emails) > 0:
            user.email_primary = emails[0]["primary"]
            user.email = emails[0]["value"]
            user.email_type = emails[0]["type"]
        groups = body.get("groups")
        if groups:
            for group in groups:
                existing_group = await Group.get_by_id(self.ctx.tenant, group["value"])
                if existing_group:
                    await GroupMembership.create(user, existing_group)
                else:
                    new_group = Group(
                        name=group["displayName"],
                        tenant=self.ctx.tenant,
                    )
                    await new_group.write()
                    await GroupMembership.create(user, new_group)
        await user.write()
        user = await User.get_by_username(
            self.ctx.tenant, user.username, get_groups=True
        )
        new_user = await user.serialize_for_scim()
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(new_user))

    async def patch(self, user_id):
        """
        Set user active status.
        """
        body = tornado.escape.json_decode(self.request.body)
        ops = body.get("Operations", [])
        if not ops:
            self.set_status(400)
            self.write(
                {
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
                    "detail": "No operations provided",
                    "status": 400,
                }
            )
            raise tornado.web.Finish()
        user = await User.get_by_id(self.ctx.tenant, user_id)
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
        is_user_active = body.get("Operations", [])[0].get("value", {}).get("active")
        user.active = is_user_active
        user.managed_by = "SCIM"
        await user.write()

    async def delete(self, user_id):
        user = await User.get_by_id(self.ctx.tenant, user_id)
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
        await user.delete()
