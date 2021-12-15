import sys
from typing import Dict, List, Optional

from okta.client import Client as OktaClient

from common.config import config
from common.lib.dynamo import UserDynamoHandler
from identity.lib.groups.models import (
    ActionResponse,
    Group,
    GroupManagementPlugin,
    OktaIdentityProvider,
    User,
)

log = config.get_logger()


class OktaGroupManagementPlugin(GroupManagementPlugin):
    def __init__(self, host, idp: OktaIdentityProvider):
        self.host = host
        self.identity_provider_name = idp.name
        okta_org_url = idp.org_url
        if not okta_org_url:
            raise Exception(
                "Unable to find URL in configuration for instantiating Okta client"
            )
        okta_api_token = idp.api_token
        if not okta_api_token:
            raise Exception(
                "API Key not found in configuration. It is required to instantiate an Okta client"
            )
        self.okta_client = OktaClient({"orgUrl": okta_org_url, "token": okta_api_token})
        self.ddb = UserDynamoHandler(self.host)
        super(OktaGroupManagementPlugin, self).__init__()

    async def create_group_request(
        self,
        users: List[User],
        groups: List[Group],
        requester: User,
        justification: Dict[str, str],
        expires: Optional[int] = None,
    ) -> ActionResponse:
        # Should return a request object
        raise NotImplementedError

    async def list_all_users(self) -> List[User]:
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "host": self.host,
            "identity_provider_name": self.identity_provider_name,
        }
        users, resp, err = await self.okta_client.list_users()
        while resp.has_next():
            next_users, resp, err = await self.okta_client.list_users()
            if err:
                log.error(
                    {
                        **log_data,
                        "message": "Error encountered when listing users",
                        "error": str(err),
                    }
                )
                return []
            users.append(next_users)

        users_to_return = []
        for user in users:
            users_to_return.append(
                User(
                    idp_name=self.identity_provider_name,
                    host=self.host,
                    username=user.profile.login,
                    status=user.status.value.lower(),
                    user_id=f"{self.identity_provider_name}-{user.profile.login}",
                    extra=dict(
                        okta_user_id=user.id,
                        created=user.created,
                    ),
                )
            )
        return users_to_return

    async def list_all_groups(self):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "host": self.host,
            "identity_provider_name": self.identity_provider_name,
        }
        groups, resp, err = await self.okta_client.list_groups()
        while resp.has_next():
            next_groups, resp, err = await self.okta_client.list_groups()
            if err:
                log.error(
                    {
                        **log_data,
                        "message": "Error encountered when listing users",
                        "error": str(err),
                    }
                )
                return [], str(err)
            groups.append(next_groups)

        groups_to_return = {}
        for group in groups:
            group_id = f"{self.identity_provider_name}-{group.profile.name}"
            groups_to_return[group_id] = Group(
                idp_name=self.identity_provider_name,
                host=self.host,
                name=group.profile.name,
                description=group.profile.description,
                group_id=group_id,
                attributes=dict(),
                extra=dict(
                    okta_group_id=group.id,
                    created=group.created,
                ),
            )
        return groups_to_return

    async def get_user(self, user_name: str):
        user, resp, err = await self.okta_client.get_user(user_name)

        user_obj = User(
            idp_name=self.identity_provider_name,
            host=self.host,
            username=user.profile.login,
            status=user.status.value.lower(),
            user_id=f"{self.identity_provider_name}-{user.profile.login}",
            extra=dict(
                okta_user_id=user.id,
                created=user.created,
            ),
        )
        user_obj.groups = await self.get_user_group_memberships(user_obj)
        # TODO: Re-cache user to DDB
        return user_obj

    async def get_user_group_memberships(self, user: User) -> List[str]:
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "host": self.host,
            "identity_provider_name": self.identity_provider_name,
            "username": user.username,
        }

        user_groups, resp, err = await self.okta_client.list_user_groups(user.username)
        while resp.has_next():
            next_user_groups, err = await resp.next()
            if err:
                log.error(
                    {
                        **log_data,
                        "message": "Error encountered when getting user group memberships",
                        "error": str(err),
                    }
                )
                return user_groups
            user_groups.append(next_user_groups)
        return [group.profile.name for group in user_groups]

    async def get_group(self, group_name):
        groups, resp, err = await self.okta_client.list_groups(
            query_params={"q": group_name}
        )
        print(groups)
        matching_group = None
        for group in groups:
            if group.profile.name == group_name:
                matching_group = group
                break
        if not matching_group:
            # TODO: Logging, metrics, better response
            raise Exception("No matching group found")
        group_id = f"{self.identity_provider_name}-{matching_group.profile.name}"
        # TODO: Merge with the special attributes in DynamoDB
        # TODO: Get Members, or use separate API call?

        self.ddb.identity_groups_table.get_item(
            Key={"host": self.host, "group_id": group_id}
        )

        group = Group(
            idp_name=self.identity_provider_name,
            host=self.host,
            name=matching_group.profile.name,
            description=matching_group.profile.description,
            group_id=group_id,
            attributes={},
            extra=dict(
                okta_group_id=matching_group.id,
                created=matching_group.created,
            ),
        )

        group.members = await self.list_group_users(group)

        # TODO: Save new group if it doesn't already exist?
        return group
        # group = await self.okta_client.get_group(matching_group.id)
        # print(group)
        # group = await self.okta_client.get_group(group.extra["okta_group_id"])

    async def add_user_to_group(self, user: User, group: Group, actor: str):
        try:
            user.extra["okta_user_id"]
        except (KeyError, TypeError):
            user = await self.get_user(user.username)
        res, err = await self.okta_client.add_user_to_group(
            group.extra["okta_group_id"], user.extra["okta_user_id"]
        )
        return res

    async def add_user_to_groups(
        self, user: User, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def remove_user_from_group(
        self, user: User, group: Group, requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def remove_user_from_groups(
        self, user: User, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def list_group_members(self, group: Group, requester: User) -> ActionResponse:
        raise NotImplementedError

    async def list_groups_members(
        self, groups: List[Group], requester: User
    ) -> ActionResponse:
        raise NotImplementedError

    async def get_users_group_memberships(self, user: List[User]) -> ActionResponse:
        raise NotImplementedError

    async def list_group_users(self, group: Group):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "host": self.host,
            "identity_provider_name": self.identity_provider_name,
            "group_id": group.group_id,
        }
        users, resp, err = await self.okta_client.list_group_users(
            group.extra["okta_group_id"]
        )
        while resp.has_next():
            next_users, resp, err = await self.okta_client.list_group_users(
                group.extra["okta_group_id"]
            )
            if err:
                log.error(
                    {
                        **log_data,
                        "message": "Error encountered when listing users in group",
                        "error": str(err),
                    }
                )
                return [], str(err)
            users.append(next_users)
        users_to_return = []
        for user in users:
            users_to_return.append(
                User(
                    idp_name=self.identity_provider_name,
                    host=self.host,
                    username=user.profile.login,
                    status=user.status.value.lower(),
                    user_id=f"{self.identity_provider_name}-{user.profile.login}",
                    attributes={},
                    extra=dict(
                        okta_user_id=user.id,
                        created=user.created,
                    ),
                )
            )
            print(user)
        return users_to_return

    async def create_group(self, group: Group):
        raise NotImplementedError

    async def add_group_target_to_role(
        self, user_id: str, user_role_id: str, group_id: str
    ):
        raise NotImplementedError

    async def create_user(self, user: User):
        raise NotImplementedError

    async def activate_user(self, user_id):
        raise NotImplementedError

    async def suspend_user(self, user_id: str):
        raise NotImplementedError

    async def unsuspend_user(self, user_id: str):
        raise NotImplementedError

    async def assign_role_to_user(self, user_id: str, req):
        raise NotImplementedError

    async def deactivate_or_delete_user(self, user_id: str):
        raise NotImplementedError

    async def assign_role_to_group(self, group: Group, req):
        # await client.assign_role_to_group(
        #                 group.id, assign_role_req_aa)
        raise NotImplementedError

    async def list_group_assigned_roles(self, group: Group):
        # await client.list_group_assigned_roles(group.id)
        raise NotImplementedError

    async def remove_role_from_group(self, group: Group):
        # await client.remove_role_from_group(group.id, ua_role.id)
        raise NotImplementedError

    async def create_application(self, req):
        raise NotImplementedError

    async def create_application_group_assignment(
        self, app, group: Group, app_group_assignment
    ):
        raise NotImplementedError

    async def list_assigned_applications_for_group(self, group: Group):
        raise NotImplementedError

    async def deactivate_application(self, app):
        raise NotImplementedError

    async def delete_application(self, app):
        raise NotImplementedError

    async def delete_group(self, group: Group):
        raise NotImplementedError


# For testing
# async def main():
#     # TODO: Fix
#     a = OktaGroupManagementPlugin(host="localhost", idp=OktaIdentityProvider.parse_obj(
#         config.get("site_configs.localhost.identity.identity_providers.okta_test")
#     ))
#     # res = await a.list_all_groups()
#     res = await a.get_group("awssg-bunker_dev-admin-1231231231")
#     print(res)
#
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())
