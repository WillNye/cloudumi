import tornado.escape

from common.handlers.base import BaseHandler
from common.lib.policies import automatic_request


class AutomaticPolicyRequestHandler(BaseHandler):
    async def post(self):
        host = self.ctx.host
        data = tornado.escape.json_decode(self.request.body)
        role_arn = data.get("role")
        if not role_arn:
            raise Exception("Role ARN not defined")

        applied = await automatic_request.create_policy(host, role_arn, data["policy"])

        self.write({"applied": applied})
