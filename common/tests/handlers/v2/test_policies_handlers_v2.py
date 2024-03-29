"""Docstring in public module."""
import os
import sys

import pytest
from mock import patch

import common.lib.noq_json as json
from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("populate_caches")
@pytest.mark.usefixtures("dynamodb")
class TestPoliciesApi(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_policies_api(self):
        from common.config import config

        headers = {
            config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@example.com",
            config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/policies?markdown=true", headers=headers, method="GET"
        )
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(len(response_j), 3)
        # TODO (SAAS-429): there is a side-effect here, need to investigate
        # self.assertEqual(len(response_j["data"]), 21)
        first_entity = response_j["data"][0]
        self.assertIn(
            first_entity["account_id"], ["012345678901", "123456789012", "123456789013"]
        )
        self.assertIn(
            first_entity["account_name"],
            ["default_account_0", "default_account_1", "default_account_2"],
        )

    @patch("common.aws.iam.policy.utils.access_analyzer_validate_policy")
    def test_policies_check_api(self, mock_access_analyzer_validate_policy):
        from common.config import config

        mock_access_analyzer_validate_policy.return_value = []

        headers = {
            config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@example.com",
            config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
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
