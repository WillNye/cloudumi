import asyncio
import urllib

import ujson as json
from tornado.testing import AsyncHTTPTestCase

from common.lib.jwt import generate_jwt_token

TEST_ACCOUNT_ID = "759357822767"
TEST_ROLE = "NullRole"
TEST_ROLE_ARN = f"arn:aws:iam::{TEST_ACCOUNT_ID}:role/{TEST_ROLE}"
TEST_USER_NAME = "testing@noq.dev"
TEST_USER_GROUPS = ["engineering@noq.dev"]
TEST_USER_DOMAIN = "corp_staging_noq_dev"


class FunctionalTest(AsyncHTTPTestCase):
    maxDiff = None
    token = asyncio.run(
        generate_jwt_token(
            TEST_USER_NAME,
            TEST_USER_GROUPS,
            TEST_USER_DOMAIN,
            eula_signed=True,
        )
    )

    def get_app(self):
        from common.config import config

        config.values["_global_"]["tornado"]["debug"] = True
        config.values["_global_"]["tornado"]["xsrf"] = False
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

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
        if not headers:
            headers = {}
        if not headers.get("Content-Type"):
            headers["Content-Type"] = "application/json"
        headers["Host"] = "corp.staging.noq.dev"
        headers["Cookie"] = f"noq_auth={self.token}"
        headers["X-Forwarded-For"] = "127.0.0.1"

        if body and body_type == "json":
            body = json.dumps(body)
        if body and body_type == "urlencode":
            body = urllib.parse.urlencode(body)
        if method == "post":
            r = self.fetch(
                path,
                body=body,
                headers=headers,
                method="POST",
                follow_redirects=follow_redirects,
                request_timeout=request_timeout,
            )
            return r
        if method == "get":
            r = self.fetch(path, body=body, headers=headers)
            return r
        raise Exception("Invalid method")
