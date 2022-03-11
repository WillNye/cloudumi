"""Docstring in public module."""
import os
import sys

import ujson as json

from util.tests.fixtures.globals import host
from util.tests.fixtures.util import ConsoleMeAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestPoliciesApi(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_policies_api(self):
        from common.config import config

        headers = {
            config.get_host_specific_key(
                "auth.user_header_name", host
            ): "user@example.com",
            config.get_host_specific_key(
                "auth.groups_header_name", host
            ): "groupa,groupb,groupc",
        }
        body = json.dumps({"filters": {}})
        response = self.fetch(
            "/api/v2/policies?markdown=true", headers=headers, method="POST", body=body
        )
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(len(response_j), 3)
        self.assertEqual(len(response_j["data"]), 19)
        first_entity = response_j["data"][0]
        self.assertEqual(first_entity["account_id"], "123456789012")
        self.assertEqual(first_entity["account_name"], "default_account")

    def test_policies_check_api(self):
        from common.config import config

        headers = {
            config.get_host_specific_key(
                "auth.user_header_name", host
            ): "user@example.com",
            config.get_host_specific_key(
                "auth.groups_header_name", host
            ): "groupa,groupb,groupc",
            "Content-type": "application/json",
        }
        body = """{
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action":["s3:GetObject"],
                "Resource": ["arn:aws:s3:::bucket1"]
            }
        }"""

        response = self.fetch(
            "/api/v2/policies/check", headers=headers, method="POST", body=body
        )
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(len(response_j), 1)
        first_error = response_j[0]
        self.assertEqual(first_error["issue"], "RESOURCE_MISMATCH")
        self.assertEqual(
            first_error["title"], "No resources match for the given action"
        )
        self.assertEqual(first_error["severity"], "MEDIUM")
