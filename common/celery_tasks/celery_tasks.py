"""
This module controls defines celery tasks and their applicable schedules. The celery beat server and workers will start
when invoked. Please add internal-only celery tasks to the celery_tasks plugin.

When ran in development mode (CONFIG_LOCATION=<location of development.yaml configuration file. To run both the celery
beat scheduler and a worker simultaneously, and to have jobs kick off starting at the next minute, run the following
command: celery -A common.celery_tasks.celery_tasks worker --loglevel=info -l DEBUG -B

"""
from __future__ import absolute_import

import json  # We use a separate SetEncoder here so we cannot use ujson
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from random import randint
from typing import Any, Dict, List, Tuple, Union

import celery
import sentry_sdk
from asgiref.sync import async_to_sync
from billiard.exceptions import SoftTimeLimitExceeded
from botocore.exceptions import ClientError
from celery import group
from celery.app.task import Context
from celery.concurrency import asynpool
from celery.schedules import crontab
from celery.signals import (
    task_failure,
    task_prerun,
    task_received,
    task_rejected,
    task_retry,
    task_revoked,
    task_success,
    task_unknown,
)

# from celery_progress.backend import ProgressRecorder
from retrying import retry
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from common.aws.iam.policy.utils import get_all_managed_policies
from common.aws.iam.role.models import IAMRole
from common.aws.organizations.utils import (
    autodiscover_aws_org_accounts,
    cache_org_structure,
    onboard_new_accounts_from_orgs,
    sync_account_names_from_orgs,
)
from common.aws.service_config.utils import execute_query
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib import noq_json as ujson
from common.lib.account_indexers import (
    cache_cloud_accounts,
    get_account_id_to_name_mapping,
)
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.access_advisor import AccessAdvisor
from common.lib.aws.cached_resources.iam import store_iam_managed_policies_for_tenant
from common.lib.aws.cloudtrail import CloudTrail
from common.lib.aws.s3 import list_buckets
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.sns import list_topics
from common.lib.aws.typeahead_cache import cache_aws_resource_details
from common.lib.aws.utils import (
    allowed_to_sync_role,
    cache_all_scps,
    get_aws_principal_owner,
    get_enabled_regions_for_account,
    remove_expired_tenant_requests,
)
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.cloud_credential_authorization_mapping import (
    generate_and_store_credential_authorization_mapping,
    generate_and_store_reverse_authorization_mapping,
)
from common.lib.cloudtrail.auto_perms import detect_cloudtrail_denies_and_update_cache
from common.lib.event_bridge.role_updates import detect_role_changes_and_update_cache
from common.lib.generic import un_wrap_json_and_dump_values
from common.lib.git import store_iam_resources_in_git
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_aws_config_history_url_for_resource
from common.lib.pynamo import NoqModel
from common.lib.redis import RedisHandler
from common.lib.self_service.typeahead import cache_self_service_typeahead
from common.lib.sentry import before_send_event
from common.lib.templated_resources import cache_resource_templates
from common.lib.tenant import get_all_tenants
from common.lib.tenant_integrations.aws import handle_tenant_integration_queue
from common.lib.terraform import cache_terraform_resources
from common.lib.timeout import Timeout
from common.lib.v2.notifications import cache_notifications_to_redis_s3
from common.models import SpokeAccount
from identity.lib.groups.groups import (
    cache_identity_groups_for_tenant,
    cache_identity_requests_for_tenant,
)
from identity.lib.users.users import cache_identity_users_for_tenant

asynpool.PROC_ALIVE_TIMEOUT = config.get(
    "_global_.celery.asynpool_proc_alive_timeout", 60.0
)
default_retry_kwargs = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_kwargs": {
        "max_retries": config.get("_global_.celery.default_max_retries", 5)
    },
}


class Celery(celery.Celery):
    def on_configure(self) -> None:
        sentry_dsn = config.get("_global_.sentry.dsn")
        if sentry_dsn:
            sentry_sdk.init(
                sentry_dsn,
                before_send=before_send_event,
                traces_sample_rate=config.get(
                    "_global_.sentry.traces_sample_rate", 0.2
                ),
                integrations=[
                    TornadoIntegration(),
                    CeleryIntegration(),
                    AioHttpIntegration(),
                    RedisIntegration(),
                ],
            )


app = Celery(
    "tasks",
    broker=config.get(
        f"_global_.celery.broker.{config.region}",
        config.get("_global_.celery.broker.global", "redis://127.0.0.1:6379/1"),
    ),
    backend=config.get(
        f"_global_.celery.backend.{config.region}",
        config.get("_global_.celery.backend.global"),
    ),
)

broker_transport_options = config.get("_global_.celery.broker_transport_options")
if broker_transport_options:
    app.conf.update({"broker_transport_options": dict(broker_transport_options)})

app.conf.result_expires = config.get("_global_.celery.result_expires", 60)
app.conf.worker_prefetch_multiplier = config.get(
    "_global_.celery.worker_prefetch_multiplier", 4
)
app.conf.task_acks_late = config.get("_global_.celery.task_acks_late", True)

if config.get("_global_.celery.purge"):
    # Useful to clear celery queue in development
    with Timeout(seconds=5, error_message="Timeout: Are you sure Redis is running?"):
        app.control.purge()

log = config.get_logger()

internal_celery_tasks = get_plugin_by_name(
    config.get("_global_.plugins.internal_celery_tasks", "cmsaas_celery_tasks")
)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

REDIS_IAM_COUNT = 1000


@app.task()
def ping() -> str:
    log_data = {"task": "pong"}
    log.info(log_data)
    return "pong"


@app.task(soft_time_limit=20)
def report_celery_last_success_metrics() -> bool:
    """
    For each celery task, this will determine the number of seconds since it has last been successful.
    Celery tasks should be emitting redis stats with a deterministic key (In our case, `f"{task}.last_success"`.
    report_celery_last_success_metrics should be ran periodically to emit metrics on when a task was last successful.
    We can then alert when tasks are not ran when intended. We should also alert when no metrics are emitted
    from this function.
    """
    # TODO: What is the tenant here?
    # TODO: How to report function args?
    red = RedisHandler().redis_sync("_global_")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function}
    current_time = int(time.time())
    global schedule
    for _, t in schedule.items():
        task = t.get("task")
        last_success = int(red.get(f"{task}.last_success") or 0)
        if last_success == 0:
            log_data["message"] = "Last Success Value is 0"
            log_data["task_last_success_key"] = f"{task}.last_success"
            log.warning(log_data)
        stats.gauge(f"{task}.time_since_last_success", current_time - last_success)
        red.set(f"{task}.time_since_last_success", current_time - last_success)
    red.set(
        f"{function}.last_success", int(time.time())
    )  # Alert if this metric is not seen

    stats.count(f"{function}.success")
    stats.timer("worker.healthy")
    return True


def get_celery_request_tags(**kwargs):
    request = kwargs.get("request")
    sender_hostname = "unknown"
    sender = kwargs.get("sender")

    if sender:
        try:
            sender_hostname = sender.hostname
        except AttributeError:
            sender_hostname = vars(sender.request).get("origin", "unknown")
    if request and not isinstance(
        request, Context
    ):  # unlike others, task_revoked sends a Context for `request`
        task_name = request.name
        task_id = request.id
        receiver_hostname = request.hostname
        request_args = request.args
        request_kwargs = request.kwargs
    else:
        try:
            task_name = sender.name
        except AttributeError:
            task_name = kwargs.pop("name", "")
        try:
            task_id = sender.request.id
        except AttributeError:
            task_id = kwargs.pop("id", "")
        try:
            receiver_hostname = sender.request.hostname
        except AttributeError:
            receiver_hostname = ""
        try:
            request_args = sender.request.args
        except AttributeError:
            request_args = ""

        try:
            request_kwargs = sender.request.kwargs
        except AttributeError:
            request_kwargs = ""

    tags = {
        "task_name": task_name,
        "task_id": task_id,
        "sender_hostname": sender_hostname,
        "receiver_hostname": receiver_hostname,
        "request_args": request_args,
        "request_kwargs": request_kwargs,
    }

    tags["expired"] = kwargs.get("expired", False)
    exception = kwargs.get("exception")
    if not exception:
        exception = kwargs.get("exc")
    if exception:
        tags["error"] = repr(exception)
        if isinstance(exception, SoftTimeLimitExceeded):
            tags["timed_out"] = True
    return tags


@task_prerun.connect
def refresh_tenant_config_in_worker(**kwargs):
    tenant = kwargs.get("kwargs", {}).get("tenant")
    if not tenant:
        return
    config.CONFIG.copy_tenant_config_dynamo_to_redis(tenant)
    config.CONFIG.tenant_configs[tenant]["last_updated"] = 0


@task_received.connect
def report_number_pending_tasks(**kwargs):
    """
    Report the number of pending tasks to our metrics broker every time a task is published. This metric can be used
    for autoscaling workers.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-received
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    tags = get_celery_request_tags(**kwargs)
    tags.pop("task_id", None)
    stats.timer("celery.new_pending_task", tags=tags)


@task_success.connect
def report_successful_task(**kwargs):
    """
    Report a generic success metric as tasks to our metrics broker every time a task finished correctly.
    This metric can be used for autoscaling workers.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-success
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    tags = get_celery_request_tags(**kwargs)
    # TODO: tenant?
    red = RedisHandler().redis_sync("_global_")
    red.set(f"_global_.{tags['task_name']}.last_success", int(time.time()))
    tags.pop("error", None)
    tags.pop("task_id", None)
    stats.timer("celery.successful_task", tags=tags)


@task_retry.connect
def report_task_retry(**kwargs):
    """
    Report a generic retry metric as tasks to our metrics broker every time a task is retroed.
    This metric can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-retry
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Retry",
    }

    # Add traceback if exception info is in the kwargs
    einfo = kwargs.get("einfo")
    if einfo:
        log_data["traceback"] = einfo.traceback

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.retried_task", tags=error_tags)


@task_failure.connect
def report_failed_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task fails. This is also called when
    a task has hit a SoftTimeLimit.
    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-failure
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Failure",
    }

    # Add traceback if exception info is in the kwargs
    einfo = kwargs.get("einfo")
    if einfo:
        log_data["traceback"] = einfo.traceback

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.failed_task", tags=error_tags)


@task_unknown.connect
def report_unknown_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a worker receives an unknown task.
    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-unknown
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Unknown",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.unknown_task", tags=error_tags)


@task_rejected.connect
def report_rejected_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task is rejected.
    The metric emited by this function can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-rejected
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Rejected",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.rejected_task", tags=error_tags)


@task_revoked.connect
def report_revoked_task(**kwargs):
    """
    Report a generic failure metric as tasks to our metrics broker every time a task is revoked.
    This metric can be used for alerting.
    https://docs.celeryproject.org/en/latest/userguide/signals.html#task-revoked
    :param sender:
    :param headers:
    :param body:
    :param kwargs:
    :return:
    """
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "message": "Celery Task Revoked",
    }

    error_tags = get_celery_request_tags(**kwargs)

    log_data.update(error_tags)
    log.error(log_data)
    error_tags.pop("error", None)
    error_tags.pop("task_id", None)
    stats.timer("celery.revoked_task", tags=error_tags)


def is_task_already_running(fun, args):
    """
    Returns True if an identical task for a given function (and arguments) is already being
    ran by Celery.
    """
    task_id = None
    if celery.current_task:
        task_id = celery.current_task.request.id
    if not task_id:
        return False
    log.debug(task_id)

    active_tasks = app.control.inspect()._request("active")
    if not active_tasks:
        return False
    for _, tasks in active_tasks.items():
        for task in tasks:
            if task.get("id") == task_id:
                continue
            if task.get("name") == fun and task.get("args") == args:
                return True
    return False


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _add_role_to_redis(redis_key: str, role_entry: Dict, tenant: str) -> None:
    """
    This function will add IAM role data to redis so that policy details can be quickly retrieved by the policies
    endpoint.
    IAM role data is stored in the `redis_key` redis key by the role's ARN.
    Parameters
    ----------
    redis_key : str
        The redis key (hash)
    role_entry : Dict
        The role entry
        Example: {'name': 'nameOfRole', 'accountId': '123456789012', 'arn': 'arn:aws:iam::123456789012:role/nameOfRole',
        'templated': None, 'ttl': 1562510908, 'policy': '<json_formatted_policy>'}
    """
    try:
        red = RedisHandler().redis_sync(tenant)
        red.hset(redis_key, str(role_entry["arn"]), str(json.dumps(role_entry)))
    except Exception as e:  # noqa
        stats.count(
            "_add_role_to_redis.error",
            tags={
                "redis_key": redis_key,
                "error": str(e),
                "role_entry": role_entry.get("arn"),
                "tenant": tenant,
            },
        )
        account_id = role_entry.get("account_id")
        if not account_id:
            account_id = role_entry.get("accountId")
        log_data = {
            "message": "Error syncing Account's IAM roles to Redis",
            "account_id": account_id,
            "tenant": tenant,
            "arn": role_entry["arn"],
            "role_entry": role_entry,
        }
        log.error(log_data, exc_info=True)
        raise


@app.task(soft_time_limit=3600)
def cache_cloudtrail_errors_by_arn_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_cloudtrail_errors_by_arn.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=7200)
def cache_cloudtrail_errors_by_arn(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    red = RedisHandler().redis_sync(tenant)
    log_data: Dict = {"function": function}
    if is_task_already_running(function, [tenant]):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data
    ct = CloudTrail()
    process_cloudtrail_errors_res: Dict = async_to_sync(ct.process_cloudtrail_errors)(
        tenant, None
    )
    cloudtrail_errors = process_cloudtrail_errors_res["error_count_by_role"]
    red.setex(
        config.get_tenant_specific_key(
            "celery.cache_cloudtrail_errors_by_arn.redis_key",
            tenant,
            f"{tenant}_CLOUDTRAIL_ERRORS_BY_ARN",
        ),
        86400,
        json.dumps(cloudtrail_errors),
    )
    if process_cloudtrail_errors_res["num_new_or_changed_notifications"] > 0:
        cache_notifications.apply_async((tenant,))
    log_data["number_of_roles_with_errors"] = len(cloudtrail_errors.keys())
    log_data["number_errors"] = sum(cloudtrail_errors.values())
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600)
def cache_policies_table_details_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_policies_table_details.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800)
def cache_policies_table_details(tenant=None) -> bool:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    items = []
    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)
    red = RedisHandler().redis_sync(tenant)
    cloudtrail_errors = {}
    cloudtrail_errors_j = red.get(
        config.get_tenant_specific_key(
            "celery.cache_cloudtrail_errors_by_arn.redis_key",
            tenant,
            f"{tenant}_CLOUDTRAIL_ERRORS_BY_ARN",
        )
    )

    if cloudtrail_errors_j:
        cloudtrail_errors = json.loads(cloudtrail_errors_j)

    s3_error_topic = config.get_tenant_specific_key(
        "redis.s3_errors", tenant, f"{tenant}_S3_ERRORS"
    )
    all_s3_errors = red.get(s3_error_topic)
    s3_errors = {}
    if all_s3_errors:
        s3_errors = json.loads(all_s3_errors)

    # IAM Roles
    all_iam_roles = []
    skip_iam_roles = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_iam_roles", tenant, False
    )
    if not skip_iam_roles:
        all_iam_roles = async_to_sync(IAMRole.query)(tenant)

        for role in all_iam_roles:
            role_details_policy = role.policy
            role_tags = role_details_policy.get("Tags", {})

            if not allowed_to_sync_role(role.arn, role_tags, tenant):
                continue

            error_count = cloudtrail_errors.get(role.arn, 0)
            s3_errors_for_arn = s3_errors.get(role.arn, [])
            for error in s3_errors_for_arn:
                error_count += int(error.get("count"))

            account_id = role.accountId
            account_name = accounts_d.get(str(account_id), "Unknown")
            resource_id = role.resourceId
            items.append(
                {
                    "account_id": account_id,
                    "account_name": account_name,
                    "arn": role.arn,
                    "technology": "AWS::IAM::Role",
                    "templated": role.templated,
                    "errors": error_count,
                    "config_history_url": async_to_sync(
                        get_aws_config_history_url_for_resource
                    )(account_id, resource_id, role.arn, "AWS::IAM::Role", tenant),
                }
            )

    # IAM Users
    skip_iam_users = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_iam_users", tenant, False
    )
    if not skip_iam_users:
        all_iam_users = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            redis_key=config.get_tenant_specific_key(
                "aws.iamusers_redis_key",
                tenant,
                f"{tenant}_IAM_USER_CACHE",
            ),
            redis_data_type="hash",
            s3_bucket=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_users_combined.s3.bucket",
                tenant,
            ),
            s3_key=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_users_combined.s3.file",
                tenant,
                "account_resource_cache/cache_all_users_v1.json.gz",
            ),
            default={},
            tenant=tenant,
        )

        for arn, details_j in all_iam_users.items():
            details = ujson.loads(details_j)
            error_count = cloudtrail_errors.get(arn, 0)
            s3_errors_for_arn = s3_errors.get(arn, [])
            for error in s3_errors_for_arn:
                error_count += int(error.get("count"))
            account_id = arn.split(":")[4]
            account_name = accounts_d.get(str(account_id), "Unknown")
            resource_id = details.get("resourceId")
            items.append(
                {
                    "account_id": account_id,
                    "account_name": account_name,
                    "arn": arn,
                    "technology": "AWS::IAM::User",
                    "templated": red.hget(
                        config.get_tenant_specific_key(
                            "templated_roles.redis_key",
                            tenant,
                            f"{tenant}_TEMPLATED_ROLES_v2",
                        ),
                        arn.lower(),
                    ),
                    "errors": error_count,
                    "config_history_url": async_to_sync(
                        get_aws_config_history_url_for_resource
                    )(account_id, resource_id, arn, "AWS::IAM::User", tenant),
                }
            )
    # S3 Buckets
    skip_s3_buckets = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_s3_buckets", tenant, False
    )
    if not skip_s3_buckets:
        s3_bucket_key: str = config.get_tenant_specific_key(
            "redis.s3_bucket_key", tenant, f"{tenant}_S3_BUCKETS"
        )
        s3_accounts = red.hkeys(s3_bucket_key)
        if s3_accounts:
            for account in s3_accounts:
                account_name = accounts_d.get(str(account), "Unknown")
                buckets = json.loads(red.hget(s3_bucket_key, account))

                for bucket in buckets:
                    bucket_arn = f"arn:aws:s3:::{bucket}"
                    s3_errors_for_arn = s3_errors.get(bucket_arn, [])

                    error_count = 0
                    for error in s3_errors_for_arn:
                        error_count += int(error.get("count"))
                    items.append(
                        {
                            "account_id": account,
                            "account_name": account_name,
                            "arn": f"arn:aws:s3:::{bucket}",
                            "technology": "AWS::S3::Bucket",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # SNS Topics
    skip_sns_topics = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_sns_topics", tenant, False
    )
    if not skip_sns_topics:
        sns_topic_key: str = config.get_tenant_specific_key(
            "redis.sns_topics_key", tenant, f"{tenant}_SNS_TOPICS"
        )
        sns_accounts = red.hkeys(sns_topic_key)
        if sns_accounts:
            for account in sns_accounts:
                account_name = accounts_d.get(str(account), "Unknown")
                topics = json.loads(red.hget(sns_topic_key, account))

                for topic in topics:
                    error_count = 0
                    items.append(
                        {
                            "account_id": account,
                            "account_name": account_name,
                            "arn": topic,
                            "technology": "AWS::SNS::Topic",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # SQS Queues
    skip_sqs_queues = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_sqs_queues", tenant, False
    )
    if not skip_sqs_queues:
        sqs_queue_key: str = config.get_tenant_specific_key(
            "redis.sqs_queues_key", tenant, f"{tenant}_SQS_QUEUES"
        )
        sqs_accounts = red.hkeys(sqs_queue_key)
        if sqs_accounts:
            for account in sqs_accounts:
                account_name = accounts_d.get(str(account), "Unknown")
                queues = json.loads(red.hget(sqs_queue_key, account))

                for queue in queues:
                    error_count = 0
                    items.append(
                        {
                            "account_id": account,
                            "account_name": account_name,
                            "arn": queue,
                            "technology": "AWS::SQS::Queue",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # Managed Policies
    skip_managed_policies = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_managed_policies",
        tenant,
        False,
    )
    if not skip_managed_policies:
        managed_policies_key: str = config.get_tenant_specific_key(
            "redis.iam_managed_policies_key",
            tenant,
            f"{tenant}_IAM_MANAGED_POLICIES",
        )
        managed_policies_accounts = red.hkeys(managed_policies_key)
        if managed_policies_accounts:
            for managed_policies_account in managed_policies_accounts:
                account_name = accounts_d.get(str(managed_policies_account), "Unknown")
                managed_policies_in_account = json.loads(
                    red.hget(managed_policies_key, managed_policies_account)
                )

                for policy_arn in managed_policies_in_account:
                    # managed policies that are managed by AWS shouldn't be added to the policies table for 2 reasons:
                    # 1. We don't manage them, can't edit them
                    # 2. There are a LOT of them and we would just end up spamming the policy table...
                    # TODO: discuss if this is okay
                    if str(managed_policies_account) not in policy_arn:
                        continue
                    error_count = 0
                    items.append(
                        {
                            "account_id": managed_policies_account,
                            "account_name": account_name,
                            "arn": policy_arn,
                            "technology": "managed_policy",
                            "templated": None,
                            "errors": error_count,
                        }
                    )

    # AWS Config Resources
    skip_aws_config_resources = config.get_tenant_specific_key(
        "cache_policies_table_details.skip_aws_config_resources",
        tenant,
        False,
    )
    if not skip_aws_config_resources:
        resources_from_aws_config_redis_key: str = config.get_tenant_specific_key(
            "aws_config_cache.redis_key",
            tenant,
            f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
        )
        resources_from_aws_config = red.hgetall(resources_from_aws_config_redis_key)
        if resources_from_aws_config:
            for arn, value in resources_from_aws_config.items():
                resource = json.loads(value)
                technology = resource["resourceType"]
                # Skip technologies that we retrieve directly
                if technology in [
                    "AWS::IAM::Role",
                    "AWS::SQS::Queue",
                    "AWS::SNS::Topic",
                    "AWS::S3::Bucket",
                    "AWS::IAM::ManagedPolicy",
                ]:
                    continue
                account_id = arn.split(":")[4]
                account_name = accounts_d.get(account_id, "Unknown")
                items.append(
                    {
                        "account_id": account_id,
                        "account_name": account_name,
                        "arn": arn,
                        "technology": technology,
                        "templated": None,
                        "errors": 0,
                    }
                )

    s3_bucket = None
    s3_key = None
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "cache_policies_table_details.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "cache_policies_table_details.s3.file",
            tenant,
            "policies_table/cache_policies_table_details_v1.json.gz",
        )
    async_to_sync(store_json_results_in_redis_and_s3)(
        items,
        redis_key=config.get_tenant_specific_key(
            "policies.redis_policies_key",
            tenant,
            f"{tenant}_ALL_POLICIES",
        ),
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        tenant=tenant,
    )
    stats.count(
        "cache_policies_table_details.success",
        tags={
            "num_roles": len(all_iam_roles),
            "tenant": tenant,
        },
    )
    return True


@app.task(bind=True, soft_time_limit=2700, **default_retry_kwargs)
def cache_iam_resources_for_account(
    self, account_id: str, tenant=None
) -> Dict[str, Any]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    # progress_recorder = ProgressRecorder(self)
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "account_id": account_id,
        "tenant": tenant,
    }
    log.debug({**log_data, "message": "Request received."})

    try:
        # Get the DynamoDB handler:
        iam_user_cache_key = f"{tenant}_IAM_USER_CACHE"
        # Only query IAM and put data in Dynamo if we're in the active region
        if config.region == config.get_tenant_specific_key(
            "celery.active_region", tenant, config.region
        ) or config.get("_global_.environment") in [
            "dev",
            "test",
        ]:
            spoke_role_name = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": account_id})
                .first.name
            )
            if not spoke_role_name:
                log.error({**log_data, "message": "No spoke role name found"})
                return
            client = boto3_cached_conn(
                "iam",
                tenant,
                None,
                account_number=account_id,
                assume_role=spoke_role_name,
                region=config.region,
                sts_client_kwargs=dict(
                    region_name=config.region,
                    endpoint_url=f"https://sts.{config.region}.amazonaws.com",
                ),
                client_kwargs=config.get_tenant_specific_key(
                    "boto3.client_kwargs", tenant, {}
                ),
                session_name=sanitize_session_name(
                    "noq_cache_iam_resources_for_account"
                ),
                read_only=True,
            )
            paginator = client.get_paginator("get_account_authorization_details")
            response_iterator = paginator.paginate()
            all_iam_resources = defaultdict(list)
            for response in response_iterator:
                if not all_iam_resources:
                    all_iam_resources = response
                else:
                    all_iam_resources["UserDetailList"].extend(
                        response["UserDetailList"]
                    )
                    all_iam_resources["GroupDetailList"].extend(
                        response["GroupDetailList"]
                    )
                    all_iam_resources["RoleDetailList"].extend(
                        response["RoleDetailList"]
                    )
                    all_iam_resources["Policies"].extend(response["Policies"])
                for k in response.keys():
                    if k not in [
                        "UserDetailList",
                        "GroupDetailList",
                        "RoleDetailList",
                        "Policies",
                        "ResponseMetadata",
                        "Marker",
                        "IsTruncated",
                    ]:
                        # Fail hard if we find something unexpected
                        raise RuntimeError("Unexpected key {0} in response".format(k))

            # Store entire response in S3
            async_to_sync(store_json_results_in_redis_and_s3)(
                all_iam_resources,
                s3_bucket=config.get_tenant_specific_key(
                    "cache_iam_resources_for_account.s3.bucket", tenant
                ),
                s3_key=config.get_tenant_specific_key(
                    "cache_iam_resources_for_account.s3.file",
                    tenant,
                    "get_account_authorization_details/get_account_authorization_details_{account_id}_v1.json.gz",
                ).format(account_id=account_id),
                tenant=tenant,
            )

            iam_users = all_iam_resources["UserDetailList"]
            iam_roles = all_iam_resources["RoleDetailList"]
            iam_policies = all_iam_resources["Policies"]

            log_data["cache_refresh_required"] = async_to_sync(
                IAMRole.sync_account_roles
            )(tenant, account_id, iam_roles)

            last_updated: int = int((datetime.utcnow()).timestamp())
            ttl: int = int((datetime.utcnow() + timedelta(hours=6)).timestamp())
            for user in iam_users:
                user_entry = {
                    "arn": user.get("Arn"),
                    "tenant": tenant,
                    "name": user.get("UserName"),
                    "resourceId": user.get("UserId"),
                    "accountId": account_id,
                    "ttl": ttl,
                    "last_updated": last_updated,
                    "owner": get_aws_principal_owner(user, tenant),
                    "policy": NoqModel().dump_json_attr(user),
                    "templated": False,  # Templates not supported for IAM users at this time
                }
                # Redis:
                _add_role_to_redis(iam_user_cache_key, user_entry, tenant)

            # Maybe store all resources in git
            if config.get_tenant_specific_key(
                "cache_iam_resources_for_account.store_in_git.enabled",
                tenant,
            ):
                store_iam_resources_in_git(all_iam_resources, account_id, tenant)

            if iam_policies:
                async_to_sync(store_iam_managed_policies_for_tenant)(
                    tenant, iam_policies, account_id
                )

        stats.count(
            "cache_iam_resources_for_account.success",
            tags={
                "account_id": account_id,
                "tenant": tenant,
            },
        )
        log.debug({**log_data, "message": "Finished caching IAM resources for account"})
    except Exception as err:
        log_data["error"] = str(err)
        log.exception(log_data)

    return log_data


@app.task(soft_time_limit=3600)
def cache_access_advisor_for_account(tenant: str, account_id: str) -> Dict[str, Any]:
    """Caches AWS access advisor data for an account that belongs to a tenant.
    This tells us which services each role has used.

    :param tenant: Tenant ID
    :param account_id: AWS Account ID
    """
    log_data = {
        "account_id": account_id,
        "tenant": tenant,
        "message": "Caching access advisor data for account",
    }

    aa = AccessAdvisor(tenant)
    res = async_to_sync(aa.generate_and_save_access_advisor_data)(tenant, account_id)
    log_data["num_roles_analyzed"] = len(res.keys())
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600)
def cache_access_advisor_across_accounts(tenant: str) -> Dict:
    """Triggers `cache_access_advisor_for_account` tasks on each AWS account that belongs to a tenant.

    :param tenant: Tenant ID
    :raises Exception: When tenant is not valid
    :return: Summary of the number of tasks triggered
    """
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "tenant": tenant,
        "message": "Caching access advisor data for tenant's accounts",
    }

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)
    log_data["num_accounts"] = len(accounts_d.keys())

    for account_id in accounts_d.keys():
        if config.get("_global_.environment") == "test":
            if account_id in config.get_tenant_specific_key(
                "celery.test_account_ids", tenant, []
            ):
                cache_access_advisor_for_account.delay(tenant, account_id)
        else:
            cache_access_advisor_for_account.delay(tenant, account_id)

    stats.count(f"{function}.success")
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600)
def cache_access_advisor_across_accounts_for_all_tenants() -> Dict:
    """Triggers `cache_access_advisor_across_accounts` task for each tenant.

    :return: Number of tenants that had tasks triggered.
    """
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        if not config.get_tenant_specific_key(
            "cache_iam_resources_for_account.check_unused_permissions.enabled",
            tenant,
            True,
        ):
            continue
        cache_access_advisor_across_accounts.delay(tenant=tenant)
    return log_data


@app.task(soft_time_limit=3600)
def cache_iam_resources_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        # TODO: Figure out why wait_for_subtask_completion=True is failing here
        cache_iam_resources_across_accounts.delay(
            tenant=tenant, wait_for_subtask_completion=False
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_iam_resources_across_accounts(
    tenant=None, run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")

    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    red = RedisHandler().redis_sync(tenant)
    cache_keys = {
        "iam_users": {
            "cache_key": f"{tenant}_IAM_USER_CACHE",
        },
    }

    log_data = {"function": function, "tenant": tenant}
    if is_task_already_running(function, [tenant]):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data

    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)(tenant)
    tasks = []
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in ["dev"]:
        # First, get list of accounts
        # Second, call tasks to enumerate all the roles across all accounts
        for account_id in accounts_d.keys():
            if config.get("_global_.environment") in ["test"]:
                log.debug(
                    {
                        **log_data,
                        "message": (
                            "`environment` configuration is set to `test`. Only running tasks "
                            "for accounts in configuration "
                            "key `celery.test_account_ids`"
                        ),
                    }
                )
                if account_id in config.get_tenant_specific_key(
                    "celery.test_account_ids", tenant, []
                ):
                    tasks.append(cache_iam_resources_for_account.s(account_id, tenant))
            else:
                tasks.append(cache_iam_resources_for_account.s(account_id, tenant))
        if run_subtasks:
            results = group(*tasks).apply_async()
            if wait_for_subtask_completion:
                # results.join() forces function to wait until all tasks are complete
                results.join(disable_sync_subtasks=False)
    else:
        log.debug(
            {
                **log_data,
                "message": (
                    "Running in non-active region. Caching roles from DynamoDB and not directly from AWS"
                ),
            }
        )

    # Delete users in Redis cache with expired TTL
    all_users = red.hgetall(cache_keys["iam_users"]["cache_key"])
    users_to_delete_from_cache = []
    for arn, user_entry_j in all_users.items():
        user_entry = json.loads(user_entry_j)
        if datetime.fromtimestamp(user_entry["ttl"]) < datetime.utcnow():
            users_to_delete_from_cache.append(arn)
    if users_to_delete_from_cache:
        red.hdel(cache_keys["iam_users"]["cache_key"], *users_to_delete_from_cache)
        for arn in users_to_delete_from_cache:
            all_users.pop(arn, None)
    if all_users:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_users,
            redis_key=cache_keys["iam_users"]["cache_key"],
            redis_data_type="hash",
            s3_bucket=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_users_combined.s3.bucket",
                tenant,
            ),
            s3_key=config.get_tenant_specific_key(
                "cache_iam_resources_across_accounts.all_users_combined.s3.file",
                tenant,
                "account_resource_cache/cache_all_users_v1.json.gz",
            ),
            tenant=tenant,
        )
        cache_aws_resource_details(all_users, tenant)

    log_data["num_iam_users"] = len(all_users)
    stats.count(f"{function}.success")
    log_data["num_accounts"] = len(accounts_d)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_managed_policies_for_account(
    account_id: str, tenant=None
) -> Dict[str, Union[str, int]]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")

    log_data = {
        "function": "cache_managed_policies_for_account",
        "account_id": account_id,
        "tenant": tenant,
    }
    spoke_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name
    )
    if not spoke_role_name:
        log.error({**log_data, "message": "No spoke role name found"})
        return
    managed_policies: List[Dict] = get_all_managed_policies(
        tenant=tenant,
        account_number=account_id,
        assume_role=spoke_role_name,
        region=config.region,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
    )
    red = RedisHandler().redis_sync(tenant)
    all_policies: List = []
    for policy in managed_policies:
        all_policies.append(policy.get("Arn"))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "message": "Successfully cached IAM managed policies for account",
        "number_managed_policies": len(all_policies),
        "tenant": tenant,
    }
    log.debug(log_data)
    stats.count(
        "cache_managed_policies_for_account",
        tags={
            "account_id": account_id,
            "num_managed_policies": len(all_policies),
            "tenant": tenant,
        },
    )

    policy_key = config.get_tenant_specific_key(
        "redis.iam_managed_policies_key",
        tenant,
        f"{tenant}_IAM_MANAGED_POLICIES",
    )
    red.hset(policy_key, account_id, json.dumps(all_policies))

    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "account_resource_cache.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "account_resource_cache.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="managed_policies", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_policies,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_managed_policies_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_managed_policies_across_accounts(tenant)
    return log_data


@app.task(soft_time_limit=3600)
def cache_managed_policies_across_accounts(tenant=None) -> bool:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    # First, get list of accounts
    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)
    # Second, call tasks to enumerate all the roles across all accounts
    for account_id in accounts_d.keys():
        if config.get("_global_.environment") == "test":
            if account_id in config.get_tenant_specific_key(
                "celery.test_account_ids", tenant, []
            ):
                cache_managed_policies_for_account.delay(account_id, tenant=tenant)
        else:
            cache_managed_policies_for_account.delay(account_id, tenant=tenant)

    stats.count(f"{function}.success")
    return True


@app.task(soft_time_limit=3600)
def cache_s3_buckets_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_s3_buckets_across_accounts.delay(
            tenant=tenant, wait_for_subtask_completion=False
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_s3_buckets_across_accounts(
    tenant=None, run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    s3_bucket_redis_key: str = config.get_tenant_specific_key(
        "redis.s3_buckets_key", tenant, f"{tenant}_S3_BUCKETS"
    )
    s3_bucket = config.get_tenant_specific_key(
        "account_resource_cache.s3_combined.bucket", tenant
    )
    s3_key = config.get_tenant_specific_key(
        "account_resource_cache.s3_combined.file",
        tenant,
        "account_resource_cache/cache_s3_combined_v1.json.gz",
    )
    red = RedisHandler().redis_sync(tenant)
    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)(tenant)
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
        "tenant": tenant,
    }
    tasks = []
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in ["dev"]:
        # Call tasks to enumerate all S3 buckets across all accounts
        for account_id in accounts_d.keys():
            if config.get("_global_.environment") == "test":
                if account_id in config.get_tenant_specific_key(
                    "celery.test_account_ids", tenant, []
                ):
                    tasks.append(cache_s3_buckets_for_account.s(account_id, tenant))
            else:
                tasks.append(cache_s3_buckets_for_account.s(account_id, tenant))

    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        all_buckets = red.hgetall(s3_bucket_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_buckets,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=s3_bucket_redis_key,
            redis_data_type="hash",
            tenant=tenant,
        )
    log.debug(
        {**log_data, "message": "Successfully cached s3 buckets across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=3600)
def cache_sqs_queues_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_sqs_queues_across_accounts.delay(
            tenant=tenant, wait_for_subtask_completion=False
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_sqs_queues_across_accounts(
    tenant=None, run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    sqs_queue_redis_key: str = config.get_tenant_specific_key(
        "redis.sqs_queues_key", tenant, f"{tenant}.SQS_QUEUES"
    )
    s3_bucket = config.get_tenant_specific_key(
        "account_resource_cache.sqs_combined.bucket", tenant
    )
    s3_key = config.get_tenant_specific_key(
        "account_resource_cache.sqs_combined.file",
        tenant,
        "account_resource_cache/cache_sqs_queues_combined_v1.json.gz",
    )
    red = RedisHandler().redis_sync(tenant)

    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)(tenant)
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
        "tenant": tenant,
    }
    tasks = []
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in ["dev"]:
        for account_id in accounts_d.keys():
            if config.get("_global_.environment") == "test":
                if account_id in config.get_tenant_specific_key(
                    "celery.test_account_ids", tenant, []
                ):
                    tasks.append(cache_sqs_queues_for_account.s(account_id, tenant))
            else:
                tasks.append(cache_sqs_queues_for_account.s(account_id, tenant))
    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        all_queues = red.hgetall(sqs_queue_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues, s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=sqs_queue_redis_key,
            redis_data_type="hash",
            tenant=tenant,
        )
    log.debug(
        {**log_data, "message": "Successfully cached SQS queues across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=3600)
def cache_sns_topics_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_sns_topics_across_accounts.delay(
            tenant=tenant, wait_for_subtask_completion=False
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_sns_topics_across_accounts(
    tenant=None, run_subtasks: bool = True, wait_for_subtask_completion: bool = True
) -> Dict[str, Any]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    red = RedisHandler().redis_sync(tenant)
    sns_topic_redis_key: str = config.get_tenant_specific_key(
        "redis.sns_topics_key", tenant, f"{tenant}_SNS_TOPICS"
    )
    s3_bucket = config.get_tenant_specific_key(
        "account_resource_cache.sns_topics_combined.bucket", tenant
    )
    s3_key = config.get_tenant_specific_key(
        "account_resource_cache.{resource_type}_topics_combined.file",
        tenant,
        "account_resource_cache/cache_{resource_type}_combined_v1.json.gz",
    ).format(resource_type="sns_topics")

    # First, get list of accounts
    accounts_d: Dict[str, str] = async_to_sync(get_account_id_to_name_mapping)(tenant)
    log_data = {
        "function": function,
        "num_accounts": len(accounts_d.keys()),
        "run_subtasks": run_subtasks,
        "wait_for_subtask_completion": wait_for_subtask_completion,
        "tenant": tenant,
    }
    tasks = []
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in ["dev"]:
        for account_id in accounts_d.keys():
            if config.get("_global_.environment") == "test":
                if account_id in config.get_tenant_specific_key(
                    "celery.test_account_ids", tenant, []
                ):
                    tasks.append(cache_sns_topics_for_account.s(account_id, tenant))
            else:
                tasks.append(cache_sns_topics_for_account.s(account_id, tenant))
    log_data["num_tasks"] = len(tasks)
    if tasks and run_subtasks:
        results = group(*tasks).apply_async()
        if wait_for_subtask_completion:
            # results.join() forces function to wait until all tasks are complete
            results.join(disable_sync_subtasks=False)
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        all_topics = red.hgetall(sns_topic_redis_key)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_topics,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=sns_topic_redis_key,
            redis_data_type="hash",
            tenant=tenant,
        )
    log.debug(
        {**log_data, "message": "Successfully cached SNS topics across known accounts"}
    )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sqs_queues_for_account(
    account_id: str, tenant=None
) -> Dict[str, Union[str, int]]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "tenant": tenant,
    }
    red = RedisHandler().redis_sync(tenant)
    all_queues: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id, tenant)
    for region in enabled_regions:
        try:
            spoke_role_name = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": account_id})
                .first.name
            )
            if not spoke_role_name:
                log.error({**log_data, "message": "No spoke role name found"})
                return
            client = boto3_cached_conn(
                "sqs",
                tenant,
                None,
                account_number=account_id,
                assume_role=spoke_role_name,
                region=region,
                read_only=True,
                sts_client_kwargs=dict(
                    region_name=config.region,
                    endpoint_url=f"https://sts.{config.region}.amazonaws.com",
                ),
                client_kwargs=config.get_tenant_specific_key(
                    "boto3.client_kwargs", tenant, {}
                ),
                session_name=sanitize_session_name("noq_cache_sqs_queues_for_account"),
            )

            paginator = client.get_paginator("list_queues")

            response_iterator = paginator.paginate(PaginationConfig={"PageSize": 1000})

            for res in response_iterator:
                for queue in res.get("QueueUrls", []):
                    arn = f"arn:aws:sqs:{region}:{account_id}:{queue.split('/')[4]}"
                    all_queues.add(arn)
        except Exception as e:
            log.error(
                {
                    **log_data,
                    "region": region,
                    "message": "Unable to sync SQS queues from region",
                    "error": str(e),
                    "tenant": tenant,
                }
            )
            sentry_sdk.capture_exception()
    sqs_queue_key: str = config.get_tenant_specific_key(
        "redis.sqs_queues_key", tenant, f"{tenant}_SQS_QUEUES"
    )
    red.hset(sqs_queue_key, account_id, json.dumps(list(all_queues)))

    log_data["message"] = "Successfully cached SQS queues for account"
    log_data["number_sqs_queues"] = len(all_queues)
    log.debug(log_data)
    stats.count(
        "cache_sqs_queues_for_account",
        tags={
            "account_id": account_id,
            "number_sqs_queues": len(all_queues),
            "tenant": tenant,
        },
    )

    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "account_resource_cache.sqs.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "account_resource_cache.{resource_type}.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(
            resource_type="sqs_queues",
            account_id=account_id,
            tenant=tenant,
        )
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_queues,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_sns_topics_for_account(
    account_id: str, tenant=None
) -> Dict[str, Union[str, int]]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    # Make sure it is regional
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "tenant": tenant,
    }
    red = RedisHandler().redis_sync(tenant)
    all_topics: set = set()
    enabled_regions = async_to_sync(get_enabled_regions_for_account)(account_id, tenant)
    for region in enabled_regions:
        try:
            spoke_role_name = (
                ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": account_id})
                .first.name
            )
            if not spoke_role_name:
                log.error({**log_data, "message": "No spoke role name found"})
                return
            topics = []
            try:
                topics = list_topics(
                    tenant=tenant,
                    account_number=account_id,
                    assume_role=spoke_role_name,
                    region=region,
                    read_only=True,
                    sts_client_kwargs=dict(
                        region_name=config.region,
                        endpoint_url=f"https://sts.{config.region}.amazonaws.com",
                    ),
                    client_kwargs=config.get_tenant_specific_key(
                        "boto3.client_kwargs", tenant, {}
                    ),
                )
            except ClientError as e:
                if "AuthorizationError" not in str(e):
                    raise
            for topic in topics:
                all_topics.add(topic["TopicArn"])
        except Exception as e:
            log.error(
                {
                    **log_data,
                    "region": region,
                    "message": "Unable to sync SNS topics from region",
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()

    sns_topic_key: str = config.get_tenant_specific_key(
        "redis.sns_topics_key", tenant, f"{tenant}_SNS_TOPICS"
    )
    red.hset(sns_topic_key, account_id, json.dumps(list(all_topics)))

    log_data["message"] = "Successfully cached SNS topics for account"
    log_data["number_sns_topics"] = len(all_topics)
    log.debug(log_data)
    stats.count(
        "cache_sns_topics_for_account",
        tags={
            "account_id": account_id,
            "number_sns_topics": len(all_topics),
            "tenant": tenant,
        },
    )

    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "account_resource_cache.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "account_resource_cache.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="sns_topics", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_topics,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_s3_buckets_for_account(
    account_id: str, tenant=None
) -> Dict[str, Union[str, int]]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    log_data = {
        "function": "cache_s3_buckets_for_account",
        "account_id": account_id,
        "tenant": tenant,
    }
    red = RedisHandler().redis_sync(tenant)
    spoke_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account_id})
        .first.name
    )
    if not spoke_role_name:
        log.error({**log_data, "message": "No spoke role name found"})
        return
    s3_buckets: List = list_buckets(
        tenant=tenant,
        account_number=account_id,
        assume_role=spoke_role_name,
        region=config.region,
        read_only=True,
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
    )
    buckets: List = []
    for bucket in s3_buckets["Buckets"]:
        buckets.append(bucket["Name"])
    s3_bucket_key: str = config.get_tenant_specific_key(
        "redis.s3_buckets_key", tenant, f"{tenant}_S3_BUCKETS"
    )
    red.hset(s3_bucket_key, account_id, json.dumps(buckets))

    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "tenant": tenant,
        "message": "Successfully cached S3 buckets for account",
        "number_s3_buckets": len(buckets),
    }
    log.debug(log_data)
    stats.count(
        "cache_s3_buckets_for_account",
        tags={
            "account_id": account_id,
            "number_s3_buckets": len(buckets),
            "tenant": tenant,
        },
    )

    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_tenant_specific_key(
            "account_resource_cache.s3.bucket", tenant
        )
        s3_key = config.get_tenant_specific_key(
            "account_resource_cache.s3.file",
            tenant,
            "account_resource_cache/cache_{resource_type}_{account_id}_v1.json.gz",
        ).format(resource_type="s3_buckets", account_id=account_id)
        async_to_sync(store_json_results_in_redis_and_s3)(
            buckets,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            tenant=tenant,
        )
    return log_data


@retry(
    stop_max_attempt_number=4,
    wait_exponential_multiplier=1000,
    wait_exponential_max=1000,
)
def _scan_redis_iam_cache(
    cache_key: str,
    index: int,
    count: int,
    tenant: str,
) -> Tuple[int, Dict[str, str]]:
    red = RedisHandler().redis_sync(tenant)
    return red.hscan(cache_key, index, count=count)


@app.task(soft_time_limit=3600, **default_retry_kwargs)
def cache_resources_from_aws_config_for_account(account_id, tenant=None) -> dict:
    from common.lib.dynamo import UserDynamoHandler

    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function: str = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "account_id": account_id,
        "tenant": tenant,
    }
    if not config.get_tenant_specific_key(
        "celery.cache_resources_from_aws_config_across_accounts.enabled",
        tenant,
        config.get_tenant_specific_key(
            f"celery.cache_resources_from_aws_config_for_account.{account_id}.enabled",
            tenant,
            True,
        ),
    ):
        log_data[
            "message"
        ] = "Skipping task: Caching resources from AWS Config is disabled."
        log.debug(log_data)
        return log_data

    s3_bucket = config.get_tenant_specific_key("aws_config_cache.s3.bucket", tenant)
    s3_key = config.get_tenant_specific_key(
        "aws_config_cache.s3.file",
        tenant,
        "aws_config_cache/cache_{account_id}_v1.json.gz",
    ).format(account_id=account_id)
    dynamo = UserDynamoHandler(tenant=tenant)
    # Only query in active region, otherwise get data from DDB
    if config.region == config.get_tenant_specific_key(
        "celery.active_region", tenant, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        results = async_to_sync(execute_query)(
            config.get_tenant_specific_key(
                "cache_all_resources_from_aws_config.aws_config.all_resources_query",
                tenant,
                "select * where accountId = '{account_id}'",
            ).format(account_id=account_id),
            tenant,
            account_id=account_id,
        )

        ttl: int = int((datetime.utcnow() + timedelta(hours=6)).timestamp())
        redis_result_set = {}
        for result in results:
            result["ttl"] = ttl
            result["tenant"] = tenant
            alternative_entity_id = "|||".join(
                [
                    result.get("accountId"),
                    result.get("awsRegion"),
                    result.get("resourceId"),
                    result.get("resourceType"),
                ]
            )
            result["entity_id"] = result.get("arn", alternative_entity_id)
            if result.get("arn"):
                if redis_result_set.get(result["arn"]):
                    continue
                redis_result_set[result["arn"]] = json.dumps(result)
        if redis_result_set:
            async_to_sync(store_json_results_in_redis_and_s3)(
                un_wrap_json_and_dump_values(redis_result_set),
                redis_key=config.get_tenant_specific_key(
                    "aws_config_cache.redis_key",
                    tenant,
                    f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
                ),
                redis_data_type="hash",
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                tenant=tenant,
            )

            dynamo.write_resource_cache_data(results)
    else:
        redis_result_set = async_to_sync(retrieve_json_data_from_redis_or_s3)(
            s3_bucket=s3_bucket, s3_key=s3_key, tenant=tenant
        )

        async_to_sync(store_json_results_in_redis_and_s3)(
            redis_result_set,
            redis_key=config.get_tenant_specific_key(
                "aws_config_cache.redis_key",
                tenant,
                f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
            ),
            redis_data_type="hash",
            tenant=tenant,
        )
    log_data["message"] = "Successfully cached resources from AWS Config for account"
    log_data["number_resources_synced"] = len(redis_result_set)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600)
def cache_resources_from_aws_config_across_accounts_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_resources_from_aws_config_across_accounts.delay(
            tenant=tenant, wait_for_subtask_completion=False
        )
    return log_data


@app.task(soft_time_limit=3600)
def cache_resources_from_aws_config_across_accounts(
    tenant=None,
    run_subtasks: bool = True,
    wait_for_subtask_completion: bool = True,
) -> Dict[str, Union[Union[str, int], Any]]:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    red = RedisHandler().redis_sync(tenant)
    resource_redis_cache_key = config.get_tenant_specific_key(
        "aws_config_cache.redis_key",
        tenant,
        f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
    )
    log_data = {
        "function": function,
        "resource_redis_cache_key": resource_redis_cache_key,
        "tenant": tenant,
    }

    if not config.get_tenant_specific_key(
        "celery.cache_resources_from_aws_config_across_accounts.enabled",
        tenant,
        True,
    ):
        log_data[
            "message"
        ] = "Skipping task: Caching resources from AWS Config is disabled."
        log.debug(log_data)
        return log_data

    tasks = []
    # First, get list of accounts
    accounts_d = async_to_sync(get_account_id_to_name_mapping)(tenant)
    # Second, call tasks to enumerate all the roles across all tenant accounts
    for account_id in accounts_d.keys():
        if config.get("_global_.environment", None) == "test":
            if account_id in config.get_tenant_specific_key(
                "celery.test_account_ids", tenant, []
            ):
                tasks.append(
                    cache_resources_from_aws_config_for_account.s(account_id, tenant)
                )
        else:
            tasks.append(
                cache_resources_from_aws_config_for_account.s(account_id, tenant)
            )
    if tasks:
        if run_subtasks:
            results = group(*tasks).apply_async()
            if wait_for_subtask_completion:
                # results.join() forces function to wait until all tasks are complete
                results_list = results.join(disable_sync_subtasks=False)
                if any(
                    result.get("cache_refresh_required", False)
                    for result in results_list
                ):
                    cache_credential_authorization_mapping.apply_async((tenant,))
                    cache_self_service_typeahead_task.apply_async((tenant,))
                    cache_policies_table_details.apply_async((tenant,))

    # Delete roles in Redis cache with expired TTL
    all_resources = red.hgetall(resource_redis_cache_key)
    if all_resources:
        expired_arns = []
        for arn, resource_entry_j in all_resources.items():
            resource_entry = ujson.loads(resource_entry_j)
            if datetime.fromtimestamp(resource_entry["ttl"]) < datetime.utcnow():
                expired_arns.append(arn)
        if expired_arns:
            for expired_arn in expired_arns:
                all_resources.pop(expired_arn, None)
            red.hdel(resource_redis_cache_key, *expired_arns)

        log_data["number_of_resources"] = len(all_resources)

        # Cache all resource ARNs into a single file. Note: This runs synchronously with this task. This task triggers
        # resource collection on all accounts to happen asynchronously. That means when we store or delete data within
        # this task, we're always going to be caching the results from the previous task.
        if config.region == config.get_tenant_specific_key(
            "celery.active_region", tenant, config.region
        ) or config.get("_global_.environment") in ["dev"]:
            # Refresh all resources after deletion of expired entries
            all_resources = red.hgetall(resource_redis_cache_key)
            s3_bucket = config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.bucket", tenant
            )
            s3_key = config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.file",
                tenant,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            )
            async_to_sync(store_json_results_in_redis_and_s3)(
                all_resources,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                tenant=tenant,
            )
    stats.count(f"{function}.success")
    return log_data


@app.task(soft_time_limit=300)
def cache_cloud_account_mapping_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_cloud_account_mapping.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=300)
def cache_cloud_account_mapping(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    account_mapping = async_to_sync(cache_cloud_accounts)(tenant)

    log_data = {
        "function": function,
        "num_accounts": len(account_mapping.accounts),
        "message": "Successfully cached cloud account mapping",
        "tenant": tenant,
    }

    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_credential_authorization_mapping_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_credential_authorization_mapping.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_credential_authorization_mapping(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "tenant": tenant,
    }
    if is_task_already_running(function, [tenant]):
        log_data["message"] = "Skipping task: An identical task is currently running"
        log.debug(log_data)
        return log_data

    authorization_mapping = async_to_sync(
        generate_and_store_credential_authorization_mapping
    )(tenant)

    reverse_mapping = async_to_sync(generate_and_store_reverse_authorization_mapping)(
        authorization_mapping, tenant
    )

    log_data["num_group_authorizations"] = len(authorization_mapping)
    log_data["num_identities"] = len(reverse_mapping)
    log.debug(
        {
            **log_data,
            "message": "Successfully cached cloud credential authorization mapping",
        }
    )
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_scps_across_organizations_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_scps_across_organizations.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_scps_across_organizations(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    scps = async_to_sync(cache_all_scps)(tenant)
    log_data = {
        "function": function,
        "message": "Successfully cached service control policies",
        "num_organizations": len(scps),
        "tenant": tenant,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_organization_structure_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_organization_structure.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_organization_structure(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"

    log_data = {
        "function": function,
        "tenant": tenant,
    }

    # Loop through all accounts and add organizations if enabled
    orgs_accounts_added = async_to_sync(autodiscover_aws_org_accounts)(tenant)
    log_data["orgs_accounts_added"] = list(orgs_accounts_added)
    # Onboard spoke accounts if enabled for org
    log_data["accounts_onboarded"] = async_to_sync(onboard_new_accounts_from_orgs)(
        tenant
    )
    # Sync account names if enabled in org
    log_data["account_names_synced"] = async_to_sync(sync_account_names_from_orgs)(
        tenant
    )

    try:
        org_structure = async_to_sync(cache_org_structure)(tenant)
        log.debug(
            {
                **log_data,
                "message": "Successfully cached organization structure",
                "num_organizations": len(org_structure),
            }
        )
    except MissingConfigurationValue as e:
        log.debug(
            {
                **log_data,
                "message": "Missing configuration value",
                "error": str(e),
            }
        )
    except Exception as err:
        log.exception(
            {
                **log_data,
                "error": str(err),
            },
            exc_info=True,
        )
        sentry_sdk.capture_exception()
        raise

    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_resource_templates_task_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_resource_templates_task.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_resource_templates_task(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    templated_file_array = async_to_sync(cache_resource_templates)(tenant)
    log_data = {
        "function": function,
        "message": "Successfully cached resource templates",
        "num_templated_files": len(templated_file_array.templated_resources),
        "tenant": tenant,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_terraform_resources_task(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    terraform_resource_details = async_to_sync(cache_terraform_resources)(tenant)
    log_data = {
        "function": function,
        "message": "Successfully cached Terraform resources",
        "num_terraform_resources": len(terraform_resource_details.terraform_resources),
        "tenant": tenant,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_terraform_resources_task_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_terraform_resources_task.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_self_service_typeahead_task_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_self_service_typeahead_task.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def cache_self_service_typeahead_task(tenant=None) -> Dict:
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    self_service_typeahead = async_to_sync(cache_self_service_typeahead)(tenant)
    log_data = {
        "function": function,
        "message": "Successfully cached IAM principals and templates for self service typeahead",
        "num_typeahead_entries": len(self_service_typeahead.typeahead_entries),
        "tenant": tenant,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def trigger_credential_mapping_refresh_from_role_changes_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        if config.get_tenant_specific_key(
            "celery.trigger_credential_mapping_refresh_from_role_changes.enabled",
            tenant,
        ):
            trigger_credential_mapping_refresh_from_role_changes.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=1800, **default_retry_kwargs)
def trigger_credential_mapping_refresh_from_role_changes(tenant=None):
    """
    This task triggers a role cache refresh for any role that a change was detected for. This feature requires an
    Event Bridge rule monitoring Cloudtrail for your accounts for IAM role mutation.
    This task will trigger a credential authorization refresh if any changes were detected.
    This task should run in all regions to force IAM roles to be refreshed in each region's cache on change.
    :return:
    """
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    if not config.get_tenant_specific_key(
        "celery.trigger_credential_mapping_refresh_from_role_changes.enabled",
        tenant,
    ):
        return {
            "function": function,
            "message": "Not running Celery task because it is not enabled.",
        }
    roles_changed = detect_role_changes_and_update_cache(app, tenant)
    log_data = {
        "function": function,
        "message": "Successfully checked role changes",
        "tenant": tenant,
        "num_roles_changed": len(roles_changed),
    }
    if roles_changed:
        # Trigger credential authorization mapping refresh. We don't want credential authorization mapping refreshes
        # running in parallel, so the cache_credential_authorization_mapping is protected to prevent parallel runs.
        # This task can run in parallel without negative impact.
        cache_credential_authorization_mapping.apply_async((tenant,), countdown=30)
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=3600, **default_retry_kwargs)
def cache_cloudtrail_denies_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        if config.get_tenant_specific_key(
            "celery.cache_cloudtrail_denies.enabled", tenant
        ):
            cache_cloudtrail_denies.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=3600, **default_retry_kwargs)
def cache_cloudtrail_denies(tenant=None, max_number_to_process=None):
    """
    This task caches access denies reported by Cloudtrail. This feature requires an
    Event Bridge rule monitoring Cloudtrail for your accounts for access deny errors.
    """
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    if not (
        config.region
        == config.get_tenant_specific_key("celery.active_region", tenant, config.region)
        or config.get("_global_.environment") in ["dev", "test"]
    ):
        return {
            "function": function,
            "message": "Not running Celery task in inactive region",
        }
    events = async_to_sync(detect_cloudtrail_denies_and_update_cache)(
        app, tenant, max_number_to_process
    )
    if events.get("new_events", 0) > 0:
        # Spawn off a task to cache errors by ARN for the UI
        cache_cloudtrail_errors_by_arn.delay(tenant=tenant)
    log_data = {
        "function": function,
        "message": "Successfully cached cloudtrail denies",
        # Total CT denies
        "num_cloudtrail_denies": events.get("num_events", 0),
        # "New" CT messages that we don't already have cached in Dynamo DB. Not a "repeated" error
        "num_new_cloudtrail_denies": events.get("new_events", 0),
        "tenant": tenant,
    }
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=60, **default_retry_kwargs)
def refresh_iam_role(role_arn, tenant=None):
    """
    This task is called on demand to asynchronously refresh an AWS IAM role in Redis/DDB
    """
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")

    account_id = role_arn.split(":")[4]
    async_to_sync(IAMRole.get)(
        tenant, account_id, role_arn, force_refresh=True, run_sync=True
    )


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_notifications_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_notifications.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_notifications(tenant=None) -> Dict[str, Any]:
    """
    This task caches notifications to be shown to end-users based on their identity or group membership.
    """
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {"function": function, "tenant": tenant}
    result = async_to_sync(cache_notifications_to_redis_s3)(tenant)
    log_data.update({**result, "message": "Successfully cached notifications"})
    log.debug(log_data)
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_identity_groups_for_tenant_t(tenant: str = None) -> Dict:
    if not tenant:
        raise Exception("tenant not provided")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Caching Identity Groups for tenant",
        "tenant": tenant,
    }
    log.debug(log_data)
    # TODO: Finish this
    async_to_sync(cache_identity_groups_for_tenant)(tenant)
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_identity_users_for_tenant_t(tenant: str = None) -> Dict:
    if not tenant:
        raise Exception("tenant not provided")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Caching Identity Users for tenant",
        "tenant": tenant,
    }
    log.debug(log_data)
    # TODO: Finish this
    async_to_sync(cache_identity_users_for_tenant)(tenant)
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_identities_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_identity_groups_for_tenant_t.apply_async((tenant,))
        cache_identity_users_for_tenant_t.apply_async((tenant,))
        # TODO: Cache identity users for all tenants
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_identity_requests_for_tenant_t(tenant: str = None) -> Dict:
    if not tenant:
        raise Exception("tenant not provided")
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Caching Identity Requests for tenant",
        "tenant": tenant,
    }
    log.debug(log_data)
    # Fetch from Dynamo. Write to Redis and S3
    async_to_sync(cache_identity_requests_for_tenant)(tenant)
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def cache_identity_requests_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        cache_identity_requests_for_tenant_t.apply_async((tenant,))
    return log_data


@app.task(soft_time_limit=600, **default_retry_kwargs)
def handle_tenant_aws_integration_queue() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    log_data = {
        "function": function,
        "message": "Handling AWS Integration Queue",
    }
    log.debug(log_data)
    res = async_to_sync(handle_tenant_integration_queue)(app)

    log.debug({**log_data, "num_events": res.get("num_events")})


@app.task(soft_time_limit=600, **default_retry_kwargs)
def get_current_celery_tasks(tenant: str = None, status: str = None) -> List[Any]:
    # TODO: We may need to build a custom DynamoDB backend to segment tasks by tenant and maintain task status
    if not tenant:
        raise Exception("tenant is required")
    if not status:
        raise Exception("Status is required")
    inspect = app.control.inspect()
    if (
        status not in ["active", "scheduled", "reserved", "registered", "revoked"]
        or not inspect
    ):
        return []
    tasks = {}
    if status == "active":
        tasks = inspect.active()
    elif status == "scheduled":
        tasks = inspect.scheduled()
    elif status == "reserved":
        tasks = inspect.reserved()
    elif status == "registered":
        tasks = inspect.registered()
    elif status == "revoked":
        tasks = inspect.revoked()

    # Filter tasks to only include the ones for the requested tenant
    filtered_tasks = []
    for k, v in tasks.items():
        for task in v:
            if task["kwargs"].get("tenant") != tenant:
                continue
            filtered_tasks.append(task)
    return filtered_tasks


@app.task(soft_time_limit=2700, **default_retry_kwargs)
def remove_expired_requests_for_tenant(tenant: str = None):
    if not tenant:
        raise Exception("`tenant` must be passed to this task.")

    async_to_sync(remove_expired_tenant_requests)(tenant)


@app.task(soft_time_limit=600, **default_retry_kwargs)
def remove_expired_requests_for_all_tenants() -> Dict:
    function = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenants = get_all_tenants()
    log_data = {
        "function": function,
        "message": "Spawning tasks",
        "num_tenants": len(tenants),
    }
    log.debug(log_data)
    for tenant in tenants:
        remove_expired_requests_for_tenant.apply_async((tenant,))

    return log_data


run_tasks_normally = not bool(
    config.get("_global_.development", False)
    and config.get("_global_._development_run_celery_tasks_1_min", False)
)
# If debug mode, we will set up the schedule to run the next minute after the job starts
time_to_start = datetime.utcnow() + timedelta(minutes=1)
dev_schedule = crontab(hour=time_to_start.hour, minute=time_to_start.minute)
schedule_minute = timedelta(minutes=1)
schedule_5_minutes = timedelta(minutes=5) if run_tasks_normally else dev_schedule
schedule_15_seconds = timedelta(seconds=15) if run_tasks_normally else dev_schedule


def get_schedule(min_schedule: int) -> Union[timedelta | crontab]:
    """
    Will return a timedelta within 10% of the provided number.
    The goal of this is to stagger schedules.
    Tasks that are scheduled less often will have a wider range with the hope this will reduce the burst rate.

    Example:
         min_schedule = 30 - The timedelta will be 27-33
         min_schedule = 360 - The timedelta will be 324-396

    :param min_schedule: The base interval, in minutes to run the task
    :return timedelta | crontab:
    """
    if not run_tasks_normally:
        return dev_schedule

    threshold = min_schedule // 10
    run_every = randint(min_schedule - threshold, min_schedule + threshold)
    return timedelta(minutes=run_every)


schedule = {
    "cache_iam_resources_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_iam_resources_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(45),
    },
    "cache_policies_table_details_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_policies_table_details_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(30),
    },
    # TODO: Get this task for a similar task working so we can alert on failing tasks or tasks that do not run as
    #  planned
    # "report_celery_last_success_metrics": {
    #     "task": "common.celery_tasks.celery_tasks.report_celery_last_success_metrics",
    #     "options": {"expires": 60},
    #     "schedule": schedule_minute,
    # },
    "cache_managed_policies_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_managed_policies_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(45),
    },
    "cache_s3_buckets_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_s3_buckets_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(45),
    },
    "cache_sqs_queues_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_sqs_queues_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(45),
    },
    "cache_sns_topics_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_sns_topics_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(45),
    },
    "cache_cloudtrail_errors_by_arn_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_cloudtrail_errors_by_arn_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "cache_resources_from_aws_config_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_resources_from_aws_config_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "cache_cloud_account_mapping_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_cloud_account_mapping_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "cache_credential_authorization_mapping_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_credential_authorization_mapping_for_all_tenants",
        "options": {"expires": 180},
        "schedule": schedule_5_minutes,
    },
    "cache_scps_across_organizations_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_scps_across_organizations_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "cache_organization_structure_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_organization_structure_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "cache_resource_templates_task_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_resource_templates_task_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(30),
    },
    "cache_self_service_typeahead_task_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_self_service_typeahead_task_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(30),
    },
    "trigger_credential_mapping_refresh_from_role_changes_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.trigger_credential_mapping_refresh_from_role_changes_for_all_tenants",
        "options": {"expires": 180},
        "schedule": schedule_minute,
    },
    "cache_cloudtrail_denies_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_cloudtrail_denies_for_all_tenants",
        "options": {"expires": 180},
        "schedule": schedule_minute,
    },
    "cache_access_advisor_across_accounts_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_access_advisor_across_accounts_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60 * 6),
    },
    # "cache_identities_for_all_tenants": {
    #     "task": "common.celery_tasks.celery_tasks.cache_identities_for_all_tenants",
    #     "options": {"expires": 180},
    #     "schedule": schedule_30_minute,
    # },
    # "cache_identity_group_requests_for_all_tenants": {
    #     "task": "common.celery_tasks.celery_tasks.cache_identity_group_requests_for_all_tenants",
    #     "options": {"expires": 180},
    #     "schedule": schedule_30_minute,
    # },
    "handle_tenant_aws_integration_queue": {
        "task": "common.celery_tasks.celery_tasks.handle_tenant_aws_integration_queue",
        "options": {"expires": 180},
        "schedule": schedule_15_seconds,
    },
    "cache_terraform_resources_task_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.cache_terraform_resources_task_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60),
    },
    "remove_expired_requests_for_all_tenants": {
        "task": "common.celery_tasks.celery_tasks.remove_expired_requests_for_all_tenants",
        "options": {"expires": 180},
        "schedule": get_schedule(60 * 6),
    },
}


if internal_celery_tasks and isinstance(internal_celery_tasks, dict):
    schedule = {**schedule, **internal_celery_tasks}

if config.get("_global_.celery.clear_tasks_for_development", False):
    schedule = {}

app.autodiscover_tasks(
    [
        "common.celery_tasks.auth",
        "common.celery_tasks.settings",
    ]
)

app.conf.beat_schedule = schedule
app.conf.timezone = "UTC"
