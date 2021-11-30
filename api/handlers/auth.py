import sys
import time

from common.config import config
from common.exceptions.exceptions import SilentException
from common.handlers.base import BaseHandler

log = config.get_logger()


class AuthHandler(BaseHandler):
    async def prepare(self):
        host = self.get_host_name()
        if not config.get_host_specific_key(f"site_configs.{host}", host):
            function: str = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log_data = {
                "function": function,
                "message": "Invalid host specified. Redirecting to main page",
            }
            log.debug(log_data)
            self.set_status(403)
            self.write(
                {
                    "type": "redirect",
                    "redirect_url": "https://noq.dev",
                    "reason": "unauthenticated",
                    "message": "Invalid host specified",
                }
            )
            raise SilentException("Invalid host specified.")
        try:
            if self.request.method.lower() in ["options", "post"]:
                return
            await super(AuthHandler, self).prepare()
        except:  # noqa
            # NoUserException
            raise

    async def get(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )

    async def post(self):
        self.write(
            {
                "authCookieExpiration": self.auth_cookie_expiration,
                "currentServerTime": int(time.time()),
            }
        )
