import sys

from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseHandler
from cloudumi_common.lib.web import handle_generic_error_response
from cloudumi_common.models import WebResponse

log = config.get_logger()


class LogOutHandler(BaseHandler):
    async def get(self):
        host = self.ctx.host
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Attempting to log out user",
            "user-agent": self.request.headers.get("User-Agent"),
            "ip": self.ip,
            "host": host,
        }
        if not config.get_host_specific_key(
            f"site_configs.{host}.auth.set_auth_cookie", host
        ):
            await handle_generic_error_response(
                self,
                "Unable to log out",
                [
                    (
                        "Configuration value `auth.set_auth_cookie` is not enabled. "
                        "ConsoleMe isn't able to delete an auth cookie if setting auth "
                        "cookies is not enabled."
                    )
                ],
                400,
                "logout_failure",
                log_data,
            )
            return
        cookie_name: str = "consoleme_auth"
        if not cookie_name:
            await handle_generic_error_response(
                self,
                "Unable to log out",
                [
                    (
                        "Configuration value `auth_cookie_name` is not set. "
                        "ConsoleMe isn't able to delete an auth cookie if the auth cookie name "
                        "is not known."
                    )
                ],
                400,
                "logout_failure",
                log_data,
            )
            return
        self.clear_cookie(cookie_name)

        extra_auth_cookies: list = config.get_host_specific_key(
            f"site_configs.{host}.auth.extra_auth_cookies", host, []
        )
        for cookie in extra_auth_cookies:
            self.clear_cookie(cookie)

        redirect_url: str = config.get_host_specific_key(
            f"site_configs.{host}.auth.logout_redirect_url", host, "/"
        )
        res = WebResponse(
            status="redirect",
            redirect_url=redirect_url,
            status_code=200,
            reason="logout_redirect",
            message="User has successfully logged out. Redirecting to landing page",
        )
        log.debug({**log_data, "message": "Successfully logged out user."})
        self.write(res.json())
