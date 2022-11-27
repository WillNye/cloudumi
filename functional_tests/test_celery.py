import concurrent
from concurrent.futures import ThreadPoolExecutor

from common.celery_tasks import celery_tasks as celery
from functional_tests.conftest import (
    TEST_ACCOUNT_ID,
    TEST_USER_DOMAIN_US,
    FunctionalTest,
)


class TestCelery(FunctionalTest):
    def test_celery(self):
        executor = ThreadPoolExecutor(max_workers=1)
        futures = []

        futures.extend(
            [
                executor.submit(
                    celery.cache_iam_resources_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_s3_buckets_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_sns_topics_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_sqs_queues_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_managed_policies_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_access_advisor_for_account,
                    TEST_USER_DOMAIN_US,
                    TEST_ACCOUNT_ID,
                ),
                executor.submit(
                    celery.cache_resources_from_aws_config_for_account,
                    TEST_ACCOUNT_ID,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_terraform_resources_task,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.handle_tenant_aws_integration_queue,
                ),
                executor.submit(
                    celery.cache_access_advisor_for_account,
                    TEST_USER_DOMAIN_US,
                    TEST_ACCOUNT_ID,
                ),
                # executor.submit(
                #     celery.cache_cloudtrail_denies,
                #     TEST_USER_DOMAIN_US,
                #     1,
                # ),
                executor.submit(
                    celery.trigger_credential_mapping_refresh_from_role_changes,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_self_service_typeahead_task,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_resource_templates_task,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_organization_structure,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_scps_across_organizations,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_credential_authorization_mapping,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_cloud_account_mapping,
                    TEST_USER_DOMAIN_US,
                ),
                executor.submit(
                    celery.cache_policies_table_details,
                    TEST_USER_DOMAIN_US,
                ),
            ]
        )
        for future in concurrent.futures.as_completed(futures):
            # This will raise an exception if one of the celery tasks failed.
            future.result()
