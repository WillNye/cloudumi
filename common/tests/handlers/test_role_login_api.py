"""Docstring in public module."""
import os
import sys

import ujson as json

from util.tests.fixtures.util import ConsoleMeAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestRoleLoginApi(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_role_api_fail(self):
        pass

        response = self.fetch(
            "/api/v2/role_login/role123",
            user="user@example.com",
            groups="groupa,groupb,groupc",
        )
        self.assertEqual(response.code, 404)
        self.assertEqual(
            json.loads(response.body),
            {
                "type": "error",
                "message": "You do not have any roles matching your search criteria. ",
            },
        )

    def test_role_api_fail_multiple_matching_roles(self):
        pass

        response = self.fetch(
            "/api/v2/role_login/role",
            user="userwithmultipleroles@example.com",
            groups="group9,group3",
        )
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(
            response_j["message"],
            "You have more than one role matching your query. Please select one.",
        )
        self.assertEqual(response_j["reason"], "multiple_roles")
        self.assertEqual(response_j["type"], "redirect")
        self.assertIn("/?arn=role&warningMessage=", response_j["redirect_url"])

    def test_role_api_success(self):
        pass

        response = self.fetch(
            "/api/v2/role_login/roleA",
            user="userwithrole@example.com",
            groups="groupa@example.com",
        )
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(response_j["type"], "redirect")
        self.assertEqual(response_j["reason"], "console_login")
        self.assertEqual(response_j["role"], "arn:aws:iam::123456789012:role/roleA")
        self.assertIn(
            "https://signin.aws.amazon.com/federation?Action=login&Issuer=YourCompany&Destination=https%3A%2F%2Fus-east-1.console.aws.amazon.com&SigninToken=",
            response_j["redirect_url"],
        )
