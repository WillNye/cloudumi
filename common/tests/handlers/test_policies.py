"""Docstring in public module."""
import os
import sys

import ujson as json
from mock import MagicMock, patch

from common.tests.conftest import MockRedisHandler, create_future
from common.tests.util import ConsoleMeAsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

mock_policy_redis = MagicMock(
    return_value=MockRedisHandler(
        return_value={
            "123456789012": (
                '["arn:aws:iam:123456789012:policy/Policy1",'
                '"arn:aws:iam:123456789012:policy/Policy2"]'
            )
        }
    )
)


class TestPolicyResourceEditHandler(ConsoleMeAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    # @patch(
    #     "api.handlers.v1.policies.ResourceTypeAheadHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    # @patch("common.lib.aws.RedisHandler", mock_policy_redis)
    # @patch("common.handlers.base.auth")
    # @patch("consoleme_saas_plugins.plugins.auth.auth.Auth")
    @patch("api.handlers.v1.policies.retrieve_json_data_from_redis_or_s3")
    def test_resource_typeahead(
        self,
        mock_retrieve_json_data_from_redis_or_s3,  # mock_auth
    ):
        pass

        # mock_auth.return_value.validate_certificate.return_value = create_future(True)
        # mock_auth.return_value.extract_user_from_certificate.return_value = create_future(
        #     {"name": "user@example.com"}
        # )
        # mock_auth.return_value.get_cert_age_seconds.return_value = create_future(100)
        # headers = {
        #     config.get(
        #         f"site_configs.{host}.auth.user_header_name"
        #     ): "user@example.com",
        #     config.get(
        #         f"site_configs.{host}.auth.groups_header_name"
        #     ): "groupa,groupb,groupc",
        # }
        # Invalid resource, no search string
        resource = "fake"
        response = self.fetch(
            f"/api/v2/policies/typeahead?resource={resource}",
            # headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 400)

        # Valid resource, no search string
        resource = "s3"
        response = self.fetch(
            f"/api/v2/policies/typeahead?resource={resource}",
            # headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 400)
        result = create_future({"123456789012": '["abucket1", "abucket2"]'})
        mock_retrieve_json_data_from_redis_or_s3.return_value = result
        account_id = "123456789012"
        resource = "s3"
        search = "a"
        response = self.fetch(
            f"/api/v2/policies/typeahead?resource={resource}&search={search}&account_id={account_id}",
            # headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 200)
        self.assertIsInstance(json.loads(response.body), list)
        self.assertEqual(
            json.loads(response.body),
            [
                {"title": "abucket1", "account_id": "123456789012"},
                {"title": "abucket2", "account_id": "123456789012"},
            ],
        )
