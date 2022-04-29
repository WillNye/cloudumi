import json
import re
import sys
from datetime import datetime
from typing import Any, Dict

import boto3
import sentry_sdk

import common.lib.aws.access_undenied as access_undenied
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import DataNotRetrievable
from common.lib.assume_role import boto3_cached_conn
from common.lib.dynamo import UserDynamoHandler
from common.models import (
    CloudtrailDetection,
    CloudtrailDetectionConfiguration,
    SpokeAccount,
)

log = config.get_logger()


def process_event(event: Dict[str, Any], account_id: str, host: object):
    access_undenied_config = access_undenied.common.Config()
    access_undenied_config.session = boto3.Session()
    access_undenied_config.account_id = access_undenied_config.session.client(
        "sts"
    ).get_caller_identity()["Account"]
    spoke_account_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name
    )
    access_undenied_config.host = host
    access_undenied_config.region = config.region
    access_undenied_config.iam_client = boto3_cached_conn(
        "iam",
        access_undenied_config.host,
        None,
        account_number=account_id,
        assume_role=spoke_account_name,
        region=access_undenied_config.region,
        sts_client_kwargs=dict(
            region_name=access_undenied_config.region,
            endpoint_url=f"https://sts.{access_undenied_config.region}.amazonaws.com",
        ),
    )

    access_undenied.cli.initialize_config_from_user_input(
        config=access_undenied_config,
        cross_account_role_name=(spoke_account_name),
        management_account_role_arn=(
            f"arn:aws:iam::{account_id}:role/{spoke_account_name}"
        ),
        output_file=sys.stdout,
        suppress_output=True,
    )
    return access_undenied.analysis.analyze(access_undenied_config, event)


def get_resource_from_cloudtrail_deny(
    event: CloudtrailDetection, raw_ct_event: Dict[str, Any]
) -> str:
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

    error_message = event.error_message
    if not error_message:
        return resource

    if "on resource: arn:aws" in event.error_message:
        resource_re = re.match(r"^.* on resource: (arn:aws:.*?$)", event.error_message)
        if resource_re and len(resource_re.groups()) == 1:
            resource = resource_re.groups()[0]
    return resource


async def detect_cloudtrail_denies_and_update_cache(
    celery_app: object,
    host: str,
) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "host": host,
    }
    configuration = (
        ModelAdapter(CloudtrailDetectionConfiguration)
        .load_config("cloudtrail", host)
        .model
    )
    if not configuration:
        log_data["message"] = "CloudTrail configuration not found"
        return log_data
    enabled = configuration.enabled
    if not enabled:
        log_data["message"] = "Cloudtrail detection is disabled for this account."
    event_ttl = configuration.event_ttl
    max_num_messages_to_process = configuration.max_messages_to_process
    dynamo = UserDynamoHandler(host=host)
    queue_arn = (
        ModelAdapter(CloudtrailDetectionConfiguration)
        .load_config("cloudtrail", host)
        .model.queue_arn
    )

    queue_name = queue_arn.split(":")[-1]
    queue_account_number = queue_arn.split(":")[4]
    queue_region = queue_arn.split(":")[3]

    # Optionally assume a role before receiving messages from the queue
    queue_assume_role = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": queue_account_number})
        .first.name
    )
    sqs_client = boto3_cached_conn(
        "sqs",
        host,
        None,
        service_type="client",
        region=queue_region,
        retry_max_attempts=2,
        account_number=queue_account_number,
        assume_role=queue_assume_role,
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
    )

    queue_url_res = sqs_client.get_queue_url(QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")
    messages_awaitable = sqs_client.receive_message(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    new_events = 0
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    reached_limit_on_num_messages_to_process = False
    all_cloudtrail_denies = dict()

    while messages:
        if num_events >= max_num_messages_to_process:
            reached_limit_on_num_messages_to_process = True
            break
        processed_messages = []
        for message in messages:
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
            epoch_event_time = int((utc_time - datetime(1970, 1, 1)).total_seconds())
            # Skip entries older than a day
            # if int(time.time()) - 86400 > epoch_event_time:
            #     continue
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

            event = CloudtrailDetection(
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

            event.resource = get_resource_from_cloudtrail_deny(event, decoded_message)
            event.request_id = (
                f"{principal_arn}-{session_name}-{event_call}-{event.resource}"
            )
            generated_policy = process_event(
                decoded_message, queue_account_number, host
            )

            if generated_policy is None:
                log.warning("Unable to process cloudtrail deny event")
                num_events += 1

            elif (
                generated_policy.assessment_result
                == access_undenied.common.AccessDeniedReason.ERROR
            ):
                log.warning(
                    f"Unable to process cloudtrail deny event: {generated_policy.error_message}"
                )
                processed_messages.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )

            elif (
                generated_policy.assessment_result
                != access_undenied.common.AccessDeniedReason.ALLOWED
            ):
                if (
                    not hasattr(generated_policy, "result_details")
                    or not generated_policy.result_details.policies
                    or len(generated_policy.result_details.policies) == 0
                ):
                    log.warning(
                        "TODO/TECH-DEBT: deal with errors when result_details is not defined"
                    )
                    processed_messages.append(
                        {
                            "Id": message["MessageId"],
                            "ReceiptHandle": message["ReceiptHandle"],
                        }
                    )
                    continue
                if "Policy" in generated_policy.result_details.policies[0]:
                    event.generated_policies = generated_policy.result_details.policies[
                        0
                    ]["Policy"]
                else:
                    event.generated_policies = generated_policy.result_details.policies[
                        0
                    ]["PolicyStatement"]
                if all_cloudtrail_denies.get(event.request_id):
                    existing_event = CloudtrailDetection.parse_obj(
                        all_cloudtrail_denies[event.request_id]
                    )
                    event.count += existing_event.count
                    all_cloudtrail_denies[event.request_id] = event.dict()
                else:
                    all_cloudtrail_denies[event.request_id] = event.dict()
                    new_events += 1
                num_events += 1
                processed_messages.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )

            else:
                log.info("Allowing event")
        if processed_messages:
            sqs_client.delete_message_batch(
                QueueUrl=queue_url, Entries=processed_messages
            )

        dynamo.batch_write_cloudtrail_events(
            all_cloudtrail_denies.values(),
            host,
        )
        messages_awaitable = sqs_client.receive_message(
            QueueUrl=queue_url, MaxNumberOfMessages=10
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
