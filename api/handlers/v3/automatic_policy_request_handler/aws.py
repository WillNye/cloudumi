import tornado.escape

from common.handlers.base import BaseAdminHandler
from common.lib.policies import automatic_request
from common.models import AutomaticPolicyRequest, Status3, WebResponse


class AutomaticPolicyRequestHandler(BaseAdminHandler):
    def check_xsrf_cookie(self):
        pass

    async def post(self):
        host = self.ctx.host
        data = tornado.escape.json_decode(self.request.body)
        if not data.get("role"):
            raise Exception("Role ARN not defined")

        # TODO: Add support to config and handle support for permission_flow. Options: auto_apply, auto_request, review
        permission_flow = "auto_apply"

        policy_request = await automatic_request.create_policy_request(
            host, self.user, AutomaticPolicyRequest(**data)
        )

        if permission_flow == "auto_apply":
            policy_request = await automatic_request.approve_policy_request(
                host, policy_request.account.account_id, self.user, policy_request.id
            )

        policy_request = automatic_request.format_extended_policy_request(
            policy_request
        )
        self.write(policy_request.dict())

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

    async def patch(self, account_id, policy_request_id):
        data = tornado.escape.json_decode(self.request.body)
        allowed_statuses = [
            Status3.applied_and_failure.value,
            Status3.applied_and_success.value,
        ]
        policy_request = await automatic_request.get_policy_request(
            self.ctx.host, account_id, self.user, policy_request_id
        )
        if not policy_request:
            self.set_status(404, "Policy Request not found")
            return

        if not data["status"] in allowed_statuses:
            self.set_status(400, f"Status must be one of {allowed_statuses}")
        elif (
            data["status"] == policy_request.status
        ):  # No point in updating if it hasn't changed
            policy_request = automatic_request.format_extended_policy_request(
                policy_request
            )
            self.write(policy_request.dict())
        else:
            policy_request.status = Status3[data["status"]]
            if await automatic_request.update_policy_request(
                self.ctx.host, policy_request
            ):
                policy_request = automatic_request.format_extended_policy_request(
                    policy_request
                )
                self.write(policy_request.dict())
            else:
                self.set_status(500, "Unable to update the policy status")
