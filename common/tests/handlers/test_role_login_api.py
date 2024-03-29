"""Docstring in public module."""
import os
import sys

import pytest

import common.lib.noq_json as json
from util.tests.fixtures.util import NOQAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRoleLoginApi(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @pytest.mark.skip(
        reason="Need to port this to a functional test. "
        "It is currently failing due to the endpoint being dependent on the DB."
    )
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

    @pytest.mark.skip(
        reason="Need to port this to a functional test. "
        "It is currently failing due to the endpoint being dependent on the DB."
    )
    @pytest.mark.usefixtures("populate_caches")
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

    @pytest.mark.skip(
        reason="Need to port this to a functional test. "
        "It is currently failing due to the endpoint being dependent on the DB."
    )
    @pytest.mark.usefixtures("populate_caches")
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
