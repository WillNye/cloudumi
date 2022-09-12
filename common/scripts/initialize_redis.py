import argparse
import concurrent.futures
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor

from asgiref.sync import async_to_sync

from common.celery_tasks import celery_tasks as celery
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.tenant import get_all_tenants

start_time = int(time.time())

parallel = True


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


parser = argparse.ArgumentParser(description="Populate cloudumi's Redis Cache")
parser.add_argument(
    "--use_celery",
    default=False,
    type=str2bool,
    help="Invoke celery tasks instead of running synchronously",
)
args = parser.parse_args()

if args.use_celery:
    # Initialize Redis locally. If use_celery is set to `True`, you must be running a celery beat and worker. You can
    # run this locally with the following command:
    # `celery -A common.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8`

    celery.cache_iam_resources_across_accounts_for_all_tenants()
    celery.cache_s3_buckets_across_accounts_for_all_tenants()
    celery.cache_sns_topics_across_accounts_for_all_tenants()
    celery.cache_sqs_queues_across_accounts_for_all_tenants()
    celery.cache_managed_policies_across_accounts_for_all_tenants()
    celery.cache_resources_from_aws_config_across_accounts_for_all_tenants()
    celery.cache_policies_table_details_for_all_tenants.apply_async(countdown=180)
    celery.cache_access_advior_across_accounts_for_all_tenants()
    celery.cache_credential_authorization_mapping_for_all_tenants.apply_async(
        countdown=180
    )

else:
    tenants = get_all_tenants()
    for tenant in tenants:
        celery.cache_cloud_account_mapping(tenant)
        accounts_d = async_to_sync(get_account_id_to_name_mapping)(
            tenant, force_sync=True
        )
        if parallel:
            executor = ThreadPoolExecutor(max_workers=os.cpu_count())
            futures = []
            for account_id in accounts_d.keys():
                futures.extend(
                    [
                        executor.submit(
                            celery.cache_iam_resources_for_account, account_id, tenant
                        ),
                        executor.submit(
                            celery.cache_s3_buckets_for_account, account_id, tenant
                        ),
                        executor.submit(
                            celery.cache_sns_topics_for_account, account_id, tenant
                        ),
                        executor.submit(
                            celery.cache_sqs_queues_for_account, account_id, tenant
                        ),
                        executor.submit(
                            celery.cache_managed_policies_for_account,
                            account_id,
                            tenant,
                        ),
                        executor.submit(
                            celery.cache_access_advisor_for_account, tenant, account_id
                        ),
                        executor.submit(
                            celery.cache_resources_from_aws_config_for_account,
                            account_id,
                            tenant,
                        ),
                    ]
                )
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                except Exception as exc:
                    print("%r generated an exception: %s" % (future, exc))
        else:
            for account_id in accounts_d.keys():
                celery.cache_iam_resources_for_account(account_id, tenant)
                celery.cache_s3_buckets_for_account(account_id, tenant)
                celery.cache_sns_topics_for_account(account_id, tenant)
                celery.cache_sqs_queues_for_account(account_id, tenant)
                celery.cache_managed_policies_for_account(account_id, tenant)
                celery.cache_access_advisor_for_account(tenant, account_id)
                celery.cache_resources_from_aws_config_for_account(account_id, tenant)
        # Forces writing config to S3
        celery.cache_iam_resources_across_accounts(
            tenant, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_s3_buckets_across_accounts(
            tenant, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_sns_topics_across_accounts(
            tenant, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_sqs_queues_across_accounts(
            tenant, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_resources_from_aws_config_across_accounts(
            tenant, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_resource_templates_task(tenant)
        celery.cache_self_service_typeahead_task(tenant)
        celery.cache_policies_table_details(tenant)
        celery.cache_credential_authorization_mapping(tenant)
        celery.cache_organization_structure(tenant)
        celery.cache_scps_across_organizations(tenant)
total_time = int(time.time()) - start_time
print(f"Done caching data in Redis. It took {total_time} seconds")
