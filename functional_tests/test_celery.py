from common.celery_tasks import celery_tasks as celery
from functional_tests.conftest import (
    TEST_ACCOUNT_ID,
    TEST_USER_DOMAIN_US,
    FunctionalTest,
)


class TestCelery(FunctionalTest):
    def test_cache_iam_resources_for_account(self):
        celery.cache_iam_resources_for_account(TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US)

    def test_cache_s3_buckets_for_account(self):
        celery.cache_s3_buckets_for_account(TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US)

    def test_cache_sns_topics_for_account(self):
        celery.cache_sns_topics_for_account(TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US)

    def test_cache_sqs_queues_for_account(self):
        celery.cache_sqs_queues_for_account(TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US)

    def test_cache_managed_policies_for_account(self):
        celery.cache_managed_policies_for_account(TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US)

    def test_cache_access_advisor_for_account(self):
        celery.cache_access_advisor_for_account(TEST_USER_DOMAIN_US, TEST_ACCOUNT_ID)

    def test_cache_resources_from_aws_config_for_account(self):
        celery.cache_resources_from_aws_config_for_account(
            TEST_ACCOUNT_ID, TEST_USER_DOMAIN_US
        )

    def test_cache_terraform_resources_task(self):
        celery.cache_terraform_resources_task(TEST_USER_DOMAIN_US)

    def test_handle_tenant_aws_integration_queue(self):
        celery.handle_tenant_aws_integration_queue()

    def test_trigger_credential_mapping_refresh_from_role_changes(self):
        celery.trigger_credential_mapping_refresh_from_role_changes(TEST_USER_DOMAIN_US)

    def test_cache_self_service_typeahead_task(self):
        celery.cache_self_service_typeahead_task(TEST_USER_DOMAIN_US)

    def test_cache_resource_templates_task(self):
        celery.cache_resource_templates_task(TEST_USER_DOMAIN_US)

    def test_cache_organization_structure(self):
        celery.cache_organization_structure(TEST_USER_DOMAIN_US)

    def test_cache_scps_across_organizations(self):
        celery.cache_scps_across_organizations(TEST_USER_DOMAIN_US)

    def test_cache_credential_authorization_mapping(self):
        celery.cache_credential_authorization_mapping(TEST_USER_DOMAIN_US)

    def test_cache_cloud_account_mapping(self):
        celery.cache_cloud_account_mapping(TEST_USER_DOMAIN_US)

    def test_cache_policies_table_details(self):
        celery.cache_policies_table_details(TEST_USER_DOMAIN_US)
