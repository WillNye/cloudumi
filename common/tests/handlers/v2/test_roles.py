import pytest
from mock import patch

import common.lib.noq_json as json
from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRolesHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from common.config import config

        self.config = config
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @pytest.mark.skip(
        reason="Need to port this to a functional test. "
        "It is currently failing due to the endpoint being dependent on the DB."
    )
    def test_get(self):
        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/roles", method="GET", headers=headers)
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertIn("eligible_roles", responseJSON)
        self.assertEqual(0, len(responseJSON["eligible_roles"]))

    # @patch(
    #     "api.handlers.v2.roles.RolesHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_create_unauthorized_user(self):
        expected = {
            "status": 403,
            "title": "Forbidden",
            "message": "User is unauthorized to create a role",
        }
        response = self.fetch("/api/v2/roles", method="POST", body="test")
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    # @patch(
    #     "api.handlers.v2.roles.RolesHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    @patch("api.handlers.v2.roles.can_create_roles")
    def test_create_authorized_user(self, mock_can_create_roles):
        mock_can_create_roles.return_value = True
        input_body = {
            "account_id": "012345678901",
            "description": "This description should be added",
            "instance_profile": "True",
        }
        expected = {
            "status": 400,
            "title": "Bad Request",
            "message": "Error validating input: 1 validation error for RoleCreationRequestModel\nRoleName\n"
            "  field required (type=value_error.missing)",
        }
        response = self.fetch(
            "/api/v2/roles", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 400)
        self.assertDictEqual(json.loads(response.body), expected)

        input_body["role_name"] = "fakeRole"
        expected = {
            "errors": 0,
            "role_created": "true",
            "action_results": [
                {
                    "status": "success",
                    "message": "Role arn:aws:iam::012345678901:role/fakeRole successfully created",
                },
                {
                    "status": "success",
                    "message": "Successfully added default Assume Role Policy Document",
                },
                {
                    "status": "success",
                    "message": "Successfully added description: This description should be added",
                },
                {
                    "status": "success",
                    "message": "Successfully added instance profile fakeRole to role fakeRole",
                },
            ],
        }
        response = self.fetch(
            "/api/v2/roles", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        self.assertDictEqual(json.loads(response.body), expected)


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestAccountRolesHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from common.config import config

        self.config = config
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get roles by account",
        }
        headers = {
            self.config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            self.config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901", method="GET", headers=headers
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRoleDetailHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch("api.handlers.v2.roles.RoleDetailHandler.authorization_flow")
    def test_delete_no_user(self, mock_auth):
        mock_auth.return_value = None
        expected = {"status": 403, "title": "Forbidden", "message": "No user detected"}
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE"
        )
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    # @patch(
    #     "api.handlers.v2.roles.RoleDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_delete_unauthorized_user(self):
        expected = {
            "status": 403,
            "title": "Forbidden",
            "message": "User is unauthorized to delete a role",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE"
        )
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    # @patch(
    #     "api.handlers.v2.roles.RoleDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    @patch("api.handlers.v2.roles.can_delete_iam_principals")
    def test_delete_authorized_user_invalid_role(self, mock_can_delete_iam_principals):
        expected = {
            "status": 500,
            "title": "Internal Server Error",
            "message": "Error occurred deleting role: An error occurred (NoSuchEntity) when calling the GetRole operation: Role fake_account_admin not found",
        }
        mock_can_delete_iam_principals.return_value = True
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE"
        )
        self.assertEqual(response.code, 500)
        self.assertDictEqual(json.loads(response.body), expected)

    # @patch(
    #     "api.handlers.v2.roles.RoleDetailHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    @patch("api.handlers.v2.roles.can_delete_iam_principals")
    def test_delete_authorized_user_valid_role(self, mock_can_delete_iam_principals):
        import boto3

        from common.config import config

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        role_name = "fake_account_admin"
        account_id = "123456789012"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        expected = {
            "status": "success",
            "message": "Successfully deleted role from account",
            "role": role_name,
            "account": account_id,
        }

        mock_can_delete_iam_principals.return_value = True

        res = self.fetch(f"/api/v2/roles/{account_id}/{role_name}", method="DELETE")
        self.assertEqual(res.code, 200)
        self.assertEqual(json.loads(res.body), expected)


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRoleDetailAppHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch("api.handlers.v2.roles.can_delete_iam_principals_app")
    def test_delete_role_by_app_denied(self, mock_can_delete_roles):
        expected = {"code": "403", "message": "Invalid Certificate"}
        mock_can_delete_roles.return_value = False
        response = self.fetch(
            "/api/v2/mtls/roles/012345678901/fake_account_admin", method="DELETE"
        )
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("iam")
@pytest.mark.usefixtures("create_default_resources")
@pytest.mark.usefixtures("dynamodb")
class TestRoleCloneHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    # @patch(
    #     "api.handlers.v2.roles.RoleCloneHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_clone_unauthorized_user(self):
        expected = {
            "status": 403,
            "title": "Forbidden",
            "message": "User is unauthorized to clone a role",
        }
        response = self.fetch("/api/v2/clone/role", method="POST", body="abcd")
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    # @patch(
    #     "api.handlers.v2.roles.RoleCloneHandler.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    @patch("api.handlers.v2.roles.can_create_roles")
    def test_clone_authorized_user(self, mock_can_create_roles):
        import boto3

        from common.config import config

        mock_can_create_roles.return_value = True
        input_body = {
            "dest_account_id": "123456789012",
            "dest_role_name": "testing_dest_role",
            "account_id": "123456789012",
            "options": {
                "tags": "False",
                "inline_policies": "True",
                "assume_role_policy": "True",
                "copy_description": "False",
                "description": "Testing this should appear",
            },
        }
        expected = {
            "status": 400,
            "title": "Bad Request",
            "message": "Error validating input: 1 validation error for CloneRoleRequestModel\nRoleName\n  "
            "field required (type=value_error.missing)",
        }
        response = self.fetch(
            "/api/v2/clone/role", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 400)
        self.assertDictEqual(json.loads(response.body), expected)

        client = boto3.client(
            "iam",
            region_name="us-east-1",
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        role_name = "fake_account_admin"
        client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument="{}",
            Description="Should not appear",
        )
        client.create_instance_profile(InstanceProfileName="testinstanceprofile")
        client.add_role_to_instance_profile(
            InstanceProfileName="testinstanceprofile", RoleName=role_name
        )

        input_body["role_name"] = role_name
        expected = {
            "errors": 0,
            "role_created": "true",
            "action_results": [
                {
                    "status": "success",
                    "message": "Role arn:aws:iam::123456789012:role/testing_dest_role successfully created",
                },
                {
                    "status": "success",
                    "message": "Successfully copied Assume Role Policy Document",
                },
                {
                    "status": "success",
                    "message": "Successfully added description: Testing this should appear",
                },
                {
                    "status": "success",
                    "message": "Successfully added instance profile testing_dest_role to role testing_dest_role",
                },
            ],
        }
        response = self.fetch(
            "/api/v2/clone/role", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        self.assertDictEqual(json.loads(response.body), expected)
