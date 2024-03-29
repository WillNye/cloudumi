import pytest
from asgiref.sync import async_to_sync
from mock import Mock, patch

import common.lib.noq_json as json
from common.lib.self_service.models import (
    SelfServiceTypeaheadModel,
    SelfServiceTypeaheadModelArray,
)
from common.models import AwsResourcePrincipalModel
from util.tests.fixtures.fixtures import create_future
from util.tests.fixtures.globals import tenant
from util.tests.fixtures.util import NOQAsyncHTTPTestCase


@pytest.mark.usefixtures("redis")
@pytest.mark.usefixtures("s3")
@pytest.mark.usefixtures("create_default_resources")
class TestTypeAheadHandler(NOQAsyncHTTPTestCase):
    def get_app(self):
        from api.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def setUp(self):
        super(TestTypeAheadHandler, self).setUp()

    # @patch(
    #     "api.handlers.v2.typeahead.ResourceTypeAheadHandlerV2.authorization_flow",
    #     MockBaseHandler.authorization_flow,
    # )
    def test_typeahead_get(self):
        from common.config import config

        headers = {
            config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(tenant)
        red.hset(
            f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
            mapping={
                "arn:aws:ec2:us-west-2:123456789013:security-group/12345": json.dumps(
                    {
                        "resourceType": "AWS::EC2::SecurityGroup",
                    }
                ),
                "arn:aws:sqs:us-east-1:123456789012:rolequeue": json.dumps(
                    {
                        "resourceType": "AWS::SQS::Queue",
                    }
                ),
                "arn:aws:sns:us-east-1:123456789012:roletopic": json.dumps(
                    {
                        "resourceType": "AWS::SNS::Topic",
                    }
                ),
                "arn:aws:iam::123456789012:role/role": json.dumps(
                    {
                        "resourceType": "AWS::IAM::Role",
                    }
                ),
            },
        )
        # Return all the things
        response = self.fetch(
            "/api/v2/typeahead/resources", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)

        self.assertEqual(len(responseJSON), 4)
        # Filter for a specific query
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 3)

        # Filter for a specific limit
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role&limit=1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific account
        response = self.fetch(
            "/api/v2/typeahead/resources?account_id=123456789013",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific resource type
        response = self.fetch(
            "/api/v2/typeahead/resources?resource_type=sqs",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # filter for region
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)

        # multifilter
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1&account_id=123456789012&typeahead=role&limit=5",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)

    def test_cache_self_service_template_and_typeahead(self):
        from common.lib.templated_resources import TemplatedFileModelArray, TemplateFile

        mock_template_file_model_array = TemplatedFileModelArray(
            templated_resources=[
                TemplateFile(
                    name="fake_test_template_1",
                    repository_name="fake_repo",
                    owner="fake_owner",
                    include_accounts=["fake_account_1"],
                    exclude_accounts=None,
                    number_of_accounts=1,
                    resource="path/to/file.yaml",
                    file_path="path/to/file.yaml",
                    web_path="http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
                    resource_type="iam_role",
                    template_language="honeybee",
                )
            ]
        )

        mock_template_typeahead_model = SelfServiceTypeaheadModel(
            details_endpoint="/api/v2/templated_resource/fake_repo/path/to/file.yaml",
            display_text="fake_test_template_1",
            icon="users",
            number_of_affected_resources=1,
            principal={
                "principal_type": "HoneybeeAwsResourceTemplate",
                "repository_name": "fake_repo",
                "resource_identifier": "path/to/file.yaml",
                "resource_url": "http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
            },
        )

        patch_cache_resource_templates_for_repository = patch(
            "common.lib.templated_resources.cache_resource_templates_for_repository",
            Mock(return_value=create_future(mock_template_file_model_array)),
        )

        # Cache resource templates, but let's not go down the rabbit hole of trying to mock a Git repo
        patch_cache_resource_templates_for_repository.start()
        from common.lib.templated_resources import cache_resource_templates

        result = async_to_sync(cache_resource_templates)(tenant)
        patch_cache_resource_templates_for_repository.stop()
        self.assertEqual(result, mock_template_file_model_array)

        # Retrieve cached resource templates and ensure it is correct
        from common.lib.templated_resources import retrieve_cached_resource_templates

        result = async_to_sync(retrieve_cached_resource_templates)(tenant)
        self.assertEqual(result, mock_template_file_model_array)

        # Cache and verify Self Service Typeahead
        from common.lib.self_service.typeahead import cache_self_service_typeahead

        result = async_to_sync(cache_self_service_typeahead)(tenant)
        self.assertIsInstance(result, SelfServiceTypeaheadModelArray)
        self.assertGreater(len(result.typeahead_entries), 15)
        expected_entry = SelfServiceTypeaheadModel(
            account="default_account_2",
            details_endpoint="/api/v2/roles/123456789012/RoleNumber5",
            display_text="RoleNumber5",
            icon="user",
            number_of_affected_resources=1,
            principal=AwsResourcePrincipalModel(
                principal_type="AwsResource",
                principal_arn="arn:aws:iam::123456789012:role/RoleNumber5",
                account_id="123456789012",
            ),
        )
        # Pre-existing role is in results
        self.assertIn(expected_entry, result.typeahead_entries)
        # HB template is in results
        self.assertIn(mock_template_typeahead_model, result.typeahead_entries)

        # Now let's mock the web requests
        from common.config import config

        headers = {
            config.get_tenant_specific_key(
                "auth.user_header_name", tenant
            ): "user@github.com",
            config.get_tenant_specific_key(
                "auth.groups_header_name", tenant
            ): "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/api/v2/templated_resource/fake_repo/path/to/file.yaml",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        response_body = json.loads(response.body)
        self.assertEqual(
            response_body,
            {
                "name": "fake_test_template_1",
                "owner": "fake_owner",
                "include_accounts": ["fake_account_1"],
                "exclude_accounts": None,
                "number_of_accounts": 1,
                "resource": "path/to/file.yaml",
                "resource_type": "iam_role",
                "repository_name": "fake_repo",
                "template_language": "honeybee",
                "web_path": "http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
                "file_path": "path/to/file.yaml",
                "content": None,
            },
        )
