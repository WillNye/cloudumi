import asyncio
from typing import Optional

import boto3

from common.config import config
from common.handlers.base import BaseHandler
from common.lib.cognito.identity import get_identity_groups, get_identity_users
from common.models import CognitoGroup, CognitoUser, WebResponse


class UserAndGroupTypeAheadHandler(BaseHandler):
    async def get(self):
        response_set = set(self.groups)
        response_set.add(self.user)
        tenant = self.ctx.tenant

        if self.is_admin:
            user_pool_id = config.get_tenant_specific_key("secrets.cognito.config.user_pool_id", tenant)
            client = boto3.client("cognito-idp", region_name=config.region)
            users_and_groups = await asyncio.gather(
                get_identity_users(user_pool_id, client),
                get_identity_groups(user_pool_id, client),
            )

            for identities in users_and_groups:
                for identity in identities:
                    if isinstance(identity, CognitoGroup):
                        if user_pool_id not in identity.GroupName:
                            response_set.add(identity.GroupName)
                    elif isinstance(identity, CognitoUser):
                        user_dict: dict = identity.dict()
                        for attr in user_dict.get("Attributes", []):
                            if attr["Name"] == "email":
                                response_set.add(attr["Value"])
                                break

        try:
            type_ahead: Optional[str] = (
                self.request.arguments.get("typeahead")[0].decode("utf-8").lower()
            )
        except TypeError:
            response = list(response_set)
        else:
            response = [identity for identity in response_set if type_ahead in identity]

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=response,
            ).json(exclude_unset=True, exclude_none=True)
        )
