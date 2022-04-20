import tornado.escape

from common.handlers.base import BaseHandler
from common.lib.policies import automatic_request
from common.models import AutomaticPolicyRequest, WebResponse


class AutomaticPolicyRequestHandler(BaseHandler):
    async def post(self):
        host = self.ctx.host
        data = tornado.escape.json_decode(self.request.body)
        if not data.get("role"):
            raise Exception("Role ARN not defined")

        # ToDo: Add support to config and handle support for permission_flow. Options: auto_apply, auto_request, review
        permission_flow = "auto_apply"

        policy_request = await automatic_request.create_policy_request(
            host, self.user, AutomaticPolicyRequest(**data)
        )

        if permission_flow == "auto_apply":
            policy_request = await automatic_request.approve_policy_request(
                host, policy_request.account.account_id, self.user, policy_request.id
            )

        self.write({"status": policy_request.status.value})

    async def get(self):
        policy_requests = await automatic_request.get_policy_requests(
            self.ctx.host, user=self.user
        )
        policy_requests = [policy_request.dict() for policy_request in policy_requests]
        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=policy_requests,
                count=len(policy_requests),
            ).json()
        )
