import asyncio
import sys
from typing import List, Tuple

from okta.client import Client as OktaClient

from cloudumi_common.config import config
from cloudumi_identity.lib.groups.models import GroupManagementPlugin, User

log = config.get_logger()


class OktaGroupManagementPlugin(GroupManagementPlugin):
    def __init__(self, host, identity_provider_name):
        self.host = host
        self.identity_provider_name = identity_provider_name
        okta_client_config = config.get(
            f"site_configs.{host}.identity_providers.{self.identity_provider_name}"
        )
        okta_org_url = okta_client_config.get("org_url")
        if not okta_org_url:
            raise Exception(
                "Unable to find URL in configuration for instantiating Okta client"
            )
        okta_api_token = okta_client_config.get("api_token")
        if not okta_api_token:
            raise Exception(
                "API Key not found in configuration. It is required to instantiate an Okta client"
            )
        self.okta_client = OktaClient({"orgUrl": okta_org_url, "token": okta_api_token})
        super(OktaGroupManagementPlugin, self).__init__()

    async def list_all_users(self) -> Tuple[List[User], str]:
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "host": self.host,
            "identity_provider_name": self.identity_provider_name,
        }
        users, resp, err = await self.okta_client.list_users()
        print("here")
        if err:
            log.error(
                {
                    **log_data,
                    "message": "Error encountered when listing users",
                    "error": str(err),
                }
            )
            return [], str(err)
        users_to_return = []
        for user in users:
            users_to_return.append(User())

    async def list_all_groups(self):
        groups, resp, err = await self.okta_client.list_groups()
        print("here")


# example of usage, list all users and print their first name and last name
async def main():
    a = OktaGroupManagementPlugin(host="localhost", identity_provider_name="okta_test")
    res = await a.list_all_users()
    print(res)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
