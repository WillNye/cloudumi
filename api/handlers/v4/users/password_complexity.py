import tornado.escape

from common.handlers.base import TornadoRequestHandler
from common.lib.password import check_password_strength
from common.models import WebResponse


class PasswordComplexityHandler(TornadoRequestHandler):
    async def post(self):
        data = tornado.escape.json_decode(self.request.body)
        password = data.get("password")
        if not password:
            return
        password_strength_errors = await check_password_strength(
            password, self.get_tenant_name()
        )

        self.write(
            WebResponse(
                success="success",
                status_code=200,
                data=password_strength_errors,
            ).dict(exclude_unset=True, exclude_none=True)
        )
