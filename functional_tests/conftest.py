import asyncio
import os
import urllib
import urllib.parse
from http.cookies import SimpleCookie

import ujson as json

# from _pytest.config import Config
# from pytest_cov.plugin import CovPlugin
from tornado import escape
from tornado.testing import AsyncHTTPTestCase

from common.lib.jwt import generate_jwt_token

TEST_ACCOUNT_ID = "759357822767"
TEST_ACCOUNT_NAME = "development"
TEST_ROLE = "FunctionalTestNullRole"
TEST_ROLE_ARN = f"arn:aws:iam::{TEST_ACCOUNT_ID}:role/{TEST_ROLE}"
TEST_USER_NAME = "user@noq.dev"
TEST_USER_GROUPS = ["engineering@noq.dev"]
TEST_USER_DOMAIN: str = os.getenv("TEST_USER_DOMAIN", "")

stage = os.getenv("STAGE", "staging")
if not TEST_USER_DOMAIN:
    if stage == "staging":
        TEST_USER_DOMAIN = "corp.staging.noq.dev"
    if stage == "prod":
        TEST_USER_DOMAIN = "corp.noq.dev"
    if stage == "dev":
        TEST_USER_DOMAIN = "localhost"
TEST_USER_DOMAIN_US = TEST_USER_DOMAIN.replace(".", "_")


# # @pytest.mark.tryfirst
# def pytest_configure(config: Config) -> None:
#     """Setup default pytest options."""
#     config.option.cov_report = {
#         "term-missing": None,
#         "html": "cov_html",
#     }
#     config.option.cov_branch = True
#     config.pluginmanager.register(
#         CovPlugin(config.option, config.pluginmanager), "_cov"
#     )
#     disable_coverage_on_deployment(config)


def disable_coverage_on_deployment(config):
    if os.getenv("STAGE", None) not in ["staging", "prod"]:
        return

    cov = config.pluginmanager.get_plugin("_cov")
    cov.options.no_cov_should_warn = False
    cov.options.no_cov = True
    if cov.cov_controller:
        cov.cov_controller.pause()


class FunctionalTest(AsyncHTTPTestCase):
    """
    Class for functional tests that handles authentication and XSRF token management.
    """

    maxDiff = None
    cookies = SimpleCookie()

    def __init__(self, *args):
        super().__init__(*args)
        self.token = None

    def get_app(self):
        """
        Returns the Tornado application instance.
        """
        from common.config import config

        config.values["_global_"]["tornado"]["debug"] = True
        config.values["_global_"]["tornado"]["xsrf"] = True
        config.values["_global_"]["development"] = False
        from api.routes import make_app

        self.config = config
        return make_app(jwt_validator=lambda x: {})

    def _render_cookie_back(self):
        """
        Converts the cookies into a string format to be passed in HTTP headers.
        """
        return "".join(
            ["%s=%s;" % (x, morsel.value) for (x, morsel) in self.cookies.items()]
        )

    def _update_cookies_return_xsrf(self, headers):
        """
        Updates the cookies from the HTTP headers.
        """
        try:
            sc = headers["Set-Cookie"]
            cookies = escape.native_str(sc)
            self.cookies.update(SimpleCookie(cookies))
            while True:
                self.cookies.update(SimpleCookie(cookies))
                if "," not in cookies:
                    break
                cookies = cookies[cookies.find(",") + 1 :]
        except KeyError as e:
            print("No cookies found in headers", e)

    def make_request(
        self,
        path,
        body=None,
        body_type="json",
        method="get",
        headers=None,
        follow_redirects=True,
        request_timeout=120,
    ):
        """
        Makes an HTTP request with authentication and xsrf, and returns the response.
        """
        if not headers:
            headers = {}
        if not headers.get("Content-Type"):
            headers["Content-Type"] = "application/json"
        headers["Host"] = TEST_USER_DOMAIN

        if not self.token:
            self.token = asyncio.run(
                generate_jwt_token(
                    TEST_USER_NAME,
                    TEST_USER_GROUPS,
                    TEST_USER_DOMAIN_US,
                    eula_signed=True,
                )
            )

        self.cookies["noq_auth"] = self.token
        headers["X-Forwarded-For"] = "127.0.0.1"

        # Get XSRF token
        if method.lower() in ["post", "put", "delete"]:
            r = self.fetch("/api/v1/auth", headers=headers)
            self._update_cookies_return_xsrf(r.headers)
            for s in ["XSRF-TOKEN", "_xsrf"]:
                if self.cookies.get(s):
                    xsrf_token = self.cookies.get(s).value
                    self.cookies["_xsrf"] = xsrf_token
                    headers["X-Xsrftoken"] = xsrf_token
                    break

        if self.cookies:
            headers["Cookie"] = self._render_cookie_back()
        if body is not None and body_type == "json":
            body = json.dumps(body)
        if body is not None and body_type == "urlencode":
            body = urllib.parse.urlencode(body)
        if method.lower() == "post":
            r = self.fetch(
                path,
                body=body,
                headers=headers,
                method="POST",
                follow_redirects=follow_redirects,
                request_timeout=request_timeout,
            )
            return r
        if method.lower() == "get":
            r = self.fetch(path, body=body, headers=headers)
            return r
        if method.lower() == "delete":
            r = self.fetch(path, body=body, headers=headers, method="DELETE")
            return r
        raise Exception("Invalid method")
