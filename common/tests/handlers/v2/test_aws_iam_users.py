import json

import pytest

from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestAwsIamUsers(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    # @patch(
    #     "api.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_fetch_nonexistent_user(self):
        response = self.fetch("/api/v2/users/123456789012/test_nonexistent_user")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.reason, "Not Found")
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": 404,
                "title": "Not Found",
                "message": "Unable to retrieve the specified user: 123456789012/test_nonexistent_user. ",
            },
        )

    # @patch(
    #     "api.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_fetch_user(self):
        response = self.fetch("/api/v2/users/123456789012/TestUser")
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        body.pop("created_time")
        self.assertDictEqual(
            body,
            {
                "name": "TestUser",
                "account_id": "123456789012",
                "account_name": "default_account_2",
                "arn": "arn:aws:iam::123456789012:user/TestUser",
                "inline_policies": [
                    {
                        "PolicyName": "SomePolicy",
                        "PolicyDocument": {
                            "Statement": [
                                {"Effect": "Deny", "Action": "*", "Resource": "*"}
                            ],
                            "Version": "2012-10-17",
                        },
                    }
                ],
                "assume_role_policy_document": None,
                "cloudtrail_details": {
                    "error_url": "",
                    "errors": {"cloudtrail_errors": []},
                },
                "s3_details": {
                    "query_url": "",
                    "error_url": "",
                    "errors": {"s3_errors": []},
                },
                "apps": {"app_details": []},
                "managed_policies": [
                    {
                        "PolicyName": "policy-one",
                        "PolicyArn": "arn:aws:iam::123456789012:policy/policy-one",
                    }
                ],
                "permissions_boundary": {},
                "read_only": None,
                "role_access_config": None,
                "tags": [],
                "effective_policy": None,
                "effective_policy_repoed": None,
                "elevated_access_config": None,
                "config_timeline_url": None,
                "templated": False,
                "template_link": None,
                "terraform": None,
                "updated_time": None,
                "last_used_time": None,
                "description": None,
                "owner": None,
            },
        )

    # @patch(
    #     "api.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_delete_user_forbidden(self):
        import boto3

        from common.config import config

        user_name = "test_delete_user_forbidden"
        iam = boto3.client(
            "iam",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        iam.create_user(UserName=user_name)
        response = self.fetch(
            f"/api/v2/users/123456789012/{user_name}", method="DELETE"
        )
        self.assertEqual(response.code, 403)
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": 403,
                "title": "Forbidden",
                "message": "User is unauthorized to delete an AWS IAM user",
            },
        )

    def test_delete_user_allowed(self):
        import boto3

        from common.config import config

        user_name = "test_delete_user_allowed"
        iam = boto3.client(
            "iam",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        iam.create_user(UserName=user_name)
        response = self.fetch(
            f"/api/v2/users/123456789012/{user_name}",
            method="DELETE",
            user=user_name,
        )
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": "success",
                "message": "Successfully deleted AWS IAM user from account",
                "iam_user_name": user_name,
                "account": "123456789012",
            },
        )
