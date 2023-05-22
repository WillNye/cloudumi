import argparse
import concurrent.futures
import os
import time
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

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


def log_start(task_name):
    print(f"Starting task: {task_name}")
    return time.time()


def log_end(task_name, start_time):
    end_time = time.time()
    print(f"Finished task: {task_name}. It took {end_time - start_time:.2f} seconds")


if args.use_celery:
    tasks = [
        celery.cache_iam_resources_across_accounts_for_all_tenants,
        celery.cache_s3_buckets_across_accounts_for_all_tenants,
        celery.cache_sns_topics_across_accounts_for_all_tenants,
        celery.cache_sqs_queues_across_accounts_for_all_tenants,
        celery.cache_managed_policies_across_accounts_for_all_tenants,
        celery.cache_resources_from_aws_config_across_accounts_for_all_tenants,
        celery.cache_access_advisor_across_accounts_for_all_tenants,
        celery.sync_iambic_templates_all_tenants,
        celery.update_providers_and_provider_definitions_all_tenants,
    ]
    async_tasks = [
        celery.cache_policies_table_details_for_all_tenants,
        celery.cache_credential_authorization_mapping_for_all_tenants,
    ]

    for task in tasks:
        start_time = log_start(task.__name__)
        task()
        log_end(task.__name__, start_time)
    for async_task in async_tasks:
        start_time = log_start(async_task.__name__)
        async_task.apply_async(countdown=180)
        log_end(async_task.__name__, start_time)

else:
    tenants = get_all_tenants()
    for tenant in tenants:
        log_start("cache_cloud_account_mapping")
        celery.cache_cloud_account_mapping(tenant)
        accounts_d = async_to_sync(get_account_id_to_name_mapping)(
            tenant, force_sync=True
        )
        tasks = [
            celery.cache_iam_resources_for_account,
            celery.cache_s3_buckets_for_account,
            celery.cache_sns_topics_for_account,
            celery.cache_sqs_queues_for_account,
            celery.cache_managed_policies_for_account,
            celery.cache_access_advisor_for_account,
            celery.cache_resources_from_aws_config_for_account,
        ]
        if parallel:
            executor = ThreadPoolExecutor(max_workers=os.cpu_count())
            futures = []

            for account_id in accounts_d.keys():
                for task in tasks:
                    log_start(f"{task.__name__} for account {account_id}")
                    futures.append(executor.submit(task, account_id, tenant))
            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                except Exception as exc:
                    print("%r generated an exception: %s" % (future, exc))
        else:
            for account_id in accounts_d.keys():
                for task in tasks:
                    start_time = log_start(f"{task.__name__} for account {account_id}")
                    task(account_id, tenant)
                    log_end(f"{task.__name__} for account {account_id}", start_time)

        post_tasks = [
            partial(
                celery.cache_iam_resources_across_accounts,
                run_subtasks=False,
                wait_for_subtask_completion=False,
            ),
            partial(
                celery.cache_s3_buckets_across_accounts,
                run_subtasks=False,
                wait_for_subtask_completion=False,
            ),
            partial(
                celery.cache_sns_topics_across_accounts,
                run_subtasks=False,
                wait_for_subtask_completion=False,
            ),
            partial(
                celery.cache_sqs_queues_across_accounts,
                run_subtasks=False,
                wait_for_subtask_completion=False,
            ),
            partial(
                celery.cache_resources_from_aws_config_across_accounts,
                run_subtasks=False,
                wait_for_subtask_completion=False,
            ),
            celery.cache_resource_templates_task,
            celery.cache_self_service_typeahead_task,
            celery.cache_policies_table_details,
            celery.cache_credential_authorization_mapping,
            celery.cache_organization_structure,
            celery.cache_scps_across_organizations,
            celery.sync_iambic_templates_for_tenant,
            celery.update_providers_and_provider_definitions_for_tenant,
        ]

        for post_task in post_tasks:
            start_time = log_start(
                post_task.func.__name__
                if isinstance(post_task, partial)
                else post_task.__name__
            )
            post_task(tenant)
            log_end(
                post_task.func.__name__
                if isinstance(post_task, partial)
                else post_task.__name__,
                start_time,
            )

total_time = int(time.time()) - start_time
print(f"Done caching data in Redis. It took {total_time} seconds")
