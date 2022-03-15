from common.handlers.base import BaseHandler
from common.lib.auth import can_admin_all


class GetClientIPAddress(BaseHandler):
    async def get(self):
        """
        Get API keys
        """
        self.set_header("Content-Type", "application/json")
        if not can_admin_all(self.user, self.groups, self.ctx.host):
            self.set_status(403)
            return
        remote_ip = (
            self.request.headers.get("X-Real-IP")
            or self.request.headers.get("X-Forwarded-For")
            or self.request.remote_ip
        )
        self.set_status(200)
        self.write({"ip": remote_ip})
