import argparse
import concurrent.futures
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor

from asgiref.sync import async_to_sync

from cloudumi_common.celery_tasks import celery_tasks as celery
from cloudumi_common.config import config
from cloudumi_common.lib.account_indexers import get_account_id_to_name_mapping
from cloudumi_common.lib.tenants import get_all_hosts

start_time = int(time.time())

parallel = False


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

# Force dynamic configuration update synchronously
# config.CONFIG.load_config_from_dynamo()

if args.use_celery:
    # Initialize Redis locally. If use_celery is set to `True`, you must be running a celery beat and worker. You can
    # run this locally with the following command:
    # `celery -A cloudumi_common.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8`

    celery.cache_iam_resources_across_accounts_for_all_hosts()
    celery.cache_s3_buckets_across_accounts_for_all_hosts()
    celery.cache_sns_topics_across_accounts_for_all_hosts()
    celery.cache_sqs_queues_across_accounts_for_all_hosts()
    celery.cache_managed_policies_across_accounts_for_all_hosts()
    # default_celery_tasks.cache_application_information()
    celery.cache_resources_from_aws_config_across_accounts_for_all_hosts()
    celery.cache_policies_table_details_for_all_hosts.apply_async(countdown=180)
    celery.cache_policy_requests_for_all_hosts()
    celery.cache_credential_authorization_mapping_for_all_hosts.apply_async(
        countdown=180
    )

else:
    hosts = get_all_hosts()
    for host in hosts:
        celery.cache_cloud_account_mapping(host)
        accounts_d = async_to_sync(get_account_id_to_name_mapping)(
            host, force_sync=True
        )
        # default_celery_tasks.cache_application_information(host)
        if parallel:
            executor = ThreadPoolExecutor(max_workers=os.cpu_count())
            futures = []
            for account_id in accounts_d.keys():
                futures.extend(
                    [
                        executor.submit(
                            celery.cache_iam_resources_for_account, account_id, host
                        ),
                        executor.submit(
                            celery.cache_s3_buckets_for_account, account_id, host
                        ),
                        executor.submit(
                            celery.cache_sns_topics_for_account, account_id, host
                        ),
                        executor.submit(
                            celery.cache_sqs_queues_for_account, account_id, host
                        ),
                        executor.submit(
                            celery.cache_managed_policies_for_account, account_id, host
                        ),
                        executor.submit(
                            celery.cache_resources_from_aws_config_for_account,
                            account_id,
                            host,
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
                celery.cache_iam_resources_for_account(account_id, host)
                celery.cache_s3_buckets_for_account(account_id, host)
                celery.cache_sns_topics_for_account(account_id, host)
                celery.cache_sqs_queues_for_account(account_id, host)
                celery.cache_managed_policies_for_account(account_id, host)
                celery.cache_resources_from_aws_config_for_account(account_id, host)
        # Forces writing config to S3
        celery.cache_iam_resources_across_accounts(
            host, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_s3_buckets_across_accounts(
            host, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_sns_topics_across_accounts(
            host, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_sqs_queues_across_accounts(
            host, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_resources_from_aws_config_across_accounts(
            host, wait_for_subtask_completion=False, run_subtasks=False
        )
        celery.cache_resource_templates_task(host)
        celery.cache_self_service_typeahead_task(host)
        celery.cache_policies_table_details(host)
        celery.cache_policy_requests(host)
        celery.cache_credential_authorization_mapping(host)
total_time = int(time.time()) - start_time
print(f"Done caching data in Redis. It took {total_time} seconds")
