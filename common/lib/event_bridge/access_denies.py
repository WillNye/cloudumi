import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import sentry_sdk
import ujson as json

from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.dynamo import UserDynamoHandler

log = config.get_logger()


async def get_resource_from_cloudtrail_deny(ct_event, raw_ct_event):
    """
    Naive attempt to determine resource from Access Deny CloudTrail event. If we can't parse it from the
    Cloudtrail message, we return `*`.
    """

    resources = [
        resource["ARN"]
        for resource in raw_ct_event.get("resources", [])
        if "ARN" in resource
    ]
    if resources:
        resource: str = max(resources, key=len)
        return resource

    event_source = raw_ct_event.get("eventSource", "")
    if event_source == "s3.amazonaws.com":
        bucket_name = raw_ct_event.get("requestParameters", {}).get("bucketName", "")
        if bucket_name:
            return f"arn:aws:s3:::{bucket_name}"

    resource = "*"

    error_message = ct_event.get("error_message", "")
    if not error_message:
        return resource

    if "on resource: arn:aws" in ct_event.get("error_message", ""):
        resource_re = re.match(
            r"^.* on resource: (arn:aws:.*?$)", ct_event["error_message"]
        )
        if resource_re and len(resource_re.groups()) == 1:
            resource = resource_re.groups()[0]
    return resource


async def generate_policy_from_cloudtrail_deny(ct_event):
    """
    Naive generation of policy from a cloudtrail deny event

    TODOS:
        * Check if resource can already perform action. If so. Check if resource policy permits the action
        * For an action with a resource, check if that resource exists (Assume role to an IAM role, for example)
        * Check if being denied for some other reason than policy allowance. IE SCP, permission boundary, etc.
    """
    if ct_event["error_code"] not in [
        "UnauthorizedOperation",
        "AccessDenied",
    ]:
        return None

    policy = {
        "Statement": [
            {
                "Action": [ct_event["event_call"]],
                "Effect": "Allow",
                "Resource": [ct_event["resource"]],
            }
        ],
        "Version": "2012-10-17",
    }
    return policy


async def detect_cloudtrail_denies_and_update_cache(
    celery_app,
    host,
    event_ttl: Optional[int] = None,
    max_num_messages_to_process: Optional[int] = None,
) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "host": host,
    }
    if not event_ttl:
        event_ttl = config.get_host_specific_key(
            "event_bridge.detect_cloudtrail_denies_and_update_cache.event_ttl",
            host,
            86400,
        )
    if not max_num_messages_to_process:
        max_num_messages_to_process = config.get_host_specific_key(
            "event_bridge.detect_cloudtrail_denies_and_update_cache.max_num_messages_to_process",
            host,
            100,
        )
    dynamo = UserDynamoHandler(host=host)
    queue_arn = config.get_host_specific_key(
        "event_bridge.detect_cloudtrail_denies_and_update_cache.queue_arn",
        host,
        "",
    ).format(region=config.region)
    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`event_bridge.detect_cloudtrail_denies_and_update_cache.queue_arn`"
        )
    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]
    # Optionally assume a role before receiving messages from the queue
    queue_assume_role = config.get_host_specific_key(
        "event_bridge.detect_cloudtrail_denies_and_update_cache.assume_role",
        host,
    )

    # Modify existing cloudtrail deny samples
    all_cloudtrail_denies_l = await dynamo.parallel_scan_table_async(
        dynamo.cloudtrail_table
    )
    all_cloudtrail_denies = {}
    for cloudtrail_deny in all_cloudtrail_denies_l:
        all_cloudtrail_denies[cloudtrail_deny["request_id"]] = cloudtrail_deny

    sqs_client = await aio_wrapper(
        boto3_cached_conn,
        "sqs",
        host,
        service_type="client",
        region=queue_region,
        retry_max_attempts=2,
        account_number=queue_account_number,
        assume_role=queue_assume_role,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )

    queue_url_res = await aio_wrapper(sqs_client.get_queue_url, QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")
    messages_awaitable = await aio_wrapper(
        sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    new_events = 0
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    reached_limit_on_num_messages_to_process = False

    while messages:
        if num_events >= max_num_messages_to_process:
            reached_limit_on_num_messages_to_process = True
            break
        processed_messages = []
        for message in messages:
            try:
                message_body = json.loads(message["Body"])
                try:
                    if "Message" in message_body:
                        decoded_message = json.loads(message_body["Message"])["detail"]
                    else:
                        decoded_message = message_body["detail"]
                except Exception as e:
                    log.error(
                        {
                            **log_data,
                            "message": "Unable to process Cloudtrail message",
                            "message_body": message_body,
                            "error": str(e),
                        }
                    )
                    sentry_sdk.capture_exception()
                    continue
                event_name = decoded_message.get("eventName")
                event_source = decoded_message.get("eventSource")
                for event_source_substitution in config.get_host_specific_key(
                    "event_bridge.detect_cloudtrail_denies_and_update_cache.event_bridge_substitutions",
                    host,
                    [".amazonaws.com"],
                ):
                    event_source = event_source.replace(event_source_substitution, "")
                event_time = decoded_message.get("eventTime")
                utc_time = datetime.strptime(event_time, "%Y-%m-%dT%H:%M:%SZ")
                epoch_event_time = int(
                    (utc_time - datetime(1970, 1, 1)).total_seconds()
                )
                # Skip entries older than a day
                if int(time.time()) - 86400 > epoch_event_time:
                    continue
                try:
                    session_name = decoded_message["userIdentity"]["arn"].split("/")[-1]
                except (
                    IndexError,
                    KeyError,
                ):  # If IAM user, there won't be a session name
                    session_name = ""
                try:
                    principal_arn = decoded_message["userIdentity"]["sessionContext"][
                        "sessionIssuer"
                    ]["arn"]
                except KeyError:  # Skip events without a parsable ARN
                    continue

                event_call = f"{event_source}:{event_name}"

                ct_event = dict(
                    host=host,
                    error_code=decoded_message.get("errorCode"),
                    error_message=decoded_message.get("errorMessage"),
                    arn=principal_arn,
                    # principal_owner=owner,
                    session_name=session_name,
                    source_ip=decoded_message["sourceIPAddress"],
                    event_call=event_call,
                    epoch_event_time=epoch_event_time,
                    ttl=epoch_event_time + event_ttl,
                    count=1,
                )
                resource = await get_resource_from_cloudtrail_deny(
                    ct_event, decoded_message
                )
                ct_event["resource"] = resource
                request_id = f"{principal_arn}-{session_name}-{event_call}-{resource}"
                ct_event["request_id"] = request_id
                generated_policy = await generate_policy_from_cloudtrail_deny(ct_event)
                if generated_policy:
                    ct_event["generated_policy"] = generated_policy

                if all_cloudtrail_denies.get(request_id):
                    existing_count = all_cloudtrail_denies[request_id].get("count", 1)
                    ct_event["count"] += existing_count
                    all_cloudtrail_denies[request_id] = ct_event
                else:
                    all_cloudtrail_denies[request_id] = ct_event
                    new_events += 1
                num_events += 1
            except Exception as e:
                log.error({**log_data, "error": str(e)}, exc_info=True)
                sentry_sdk.capture_exception()
            processed_messages.append(
                {
                    "Id": message["MessageId"],
                    "ReceiptHandle": message["ReceiptHandle"],
                }
            )
        if processed_messages:
            await aio_wrapper(
                sqs_client.delete_message_batch,
                QueueUrl=queue_url,
                Entries=processed_messages,
            )

        await aio_wrapper(
            dynamo.batch_write_cloudtrail_events,
            all_cloudtrail_denies.values(),
            host,
        )
        messages_awaitable = await aio_wrapper(
            sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    if reached_limit_on_num_messages_to_process:
        # We hit our limit. Let's spawn another task immediately to process remaining messages
        celery_app.send_task(
            "common.celery_tasks.celery_tasks.cache_cloudtrail_denies",
            args=(host,),
        )
    log_data["message"] = "Successfully cached Cloudtrail Access Denies"
    log_data["num_events"] = num_events
    log_data["new_events"] = new_events
    log.debug(log_data)

    return log_data
