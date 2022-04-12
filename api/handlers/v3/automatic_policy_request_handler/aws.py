import asyncio
import random
import string

import tornado.escape
import ujson as json
from asgiref.sync import sync_to_async

from common.config import config
from common.config.models import ModelAdapter
from common.handlers.base import BaseHandler
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.sanitize import sanitize_session_name
from common.models import SpokeAccount


class AutomaticPolicyRequestHandler(BaseHandler):
    async def post(self):
        host = self.ctx.host
        data = tornado.escape.json_decode(self.request.body)
        role_arn = data.get("role")
        if not role_arn:
            raise Exception("Role ARN not defined")
        # TODO: If role_arn, check to see if role_arn is flagged as in_development, and if self.user is authorized for this role
        # TODO: Log all requests and actions taken during the session. eg: Google analytics for IAM
        account_id = role_arn.split(":")[4]
        principal_name = role_arn.split("/")[-1]
        # TODO: Support draft policies, we keep updating the draft with new changes until the user wants to submit it? Not as "aha!"
        # TODO: Normalize the policy, make sure the identity doesn't already have the allowance, and send the request. In our case, make the change.
        spoke_role_name = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name
        )
        if not spoke_role_name:
            return
        iam_client = boto3_cached_conn(
            "iam",
            host,
            account_number=account_id,
            assume_role=spoke_role_name,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            session_name=sanitize_session_name("noq_automatic_policy_request_handler"),
        )
        letters = string.ascii_lowercase
        policy_name = "".join(random.choice(letters) for i in range(10))
        # TODO: Need to ask the policy the question if it already can do what is in the permission
        # TODO: Generate formal permission request / audit trail
        # TODO: Generate more meaningful policy name
        # TODO: Generate cross-account resources as well
        await sync_to_async(iam_client.put_role_policy)(
            RoleName=principal_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(
                data["policy"],
                escape_forward_slashes=False,
            ),
        )
        await asyncio.sleep(5)
