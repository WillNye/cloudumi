import sys
from typing import Any, Dict, Optional

import boto3
import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest

from cloudumi_common.config import config
from cloudumi_common.exceptions.exceptions import (
    DataNotRetrievable,
    MissingConfigurationValue,
)
from cloudumi_common.lib.assume_role import boto3_cached_conn
from cloudumi_common.lib.dynamo import RestrictedDynamoHandler

log = config.get_logger()


async def return_error_response_for_noq_registration(
    host: str,
    status: int,
    failure_message: str,
    message: Dict[str, str],
    physical_resource_id: str,
) -> None:
    """
    Emit an S3 error event to CloudFormation.
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "status": status,
        "failure_message": failure_message,
        "host": host,
        "event_message": message,
        "physical_resource_id": physical_resource_id,
        "message": "Responding to CF NOQ Registration with error",
    }

    http_client = AsyncHTTPClient(force_instance=True)

    response_url = message.get("ResponseURL")
    response_data = {
        "Status": "FAILED",
        "Reason": failure_message,
        "PhysicalResourceId": physical_resource_id,
        "StackId": message.get("StackId"),
        "RequestId": message.get("RequestId"),
        "LogicalResourceId": message.get("LogicalResourceId"),
    }

    response_data_json = json.dumps(response_data)
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response_data_json)),
    }

    http_req = HTTPRequest(
        url=response_url,
        method="PUT",
        headers=headers,
        body=json.dumps(response_data),
    )
    try:
        resp = await http_client.fetch(request=http_req)
        log_data["message"] = "Slack notification sent"
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending notification to CF"
        log_data["error"] = str(e)
        log.error(log_data)
        sentry_sdk.capture_exception()
        return {"statusCode": status, "body": None}

    return {"statusCode": status, "body": resp.body}


async def handle_tenant_integration_queue(
    celery_app,
    max_num_messages_to_process: Optional[int] = None,
) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }

    if not max_num_messages_to_process:
        max_num_messages_to_process = config.get(
            "_global_.noq_registration.max_num_messages_to_process",
            100,
        )

    # TODO: Put this in configuration: queue_arn = "arn:aws:sqs:us-east-1:259868150464:noq_registration_queue"
    queue_arn = config.get(
        "_global_.noq_registration.queue_arn",
        "arn:aws:sqs:us-east-1:259868150464:noq_registration_queue",
    )
    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`_global_.noq_registration.queue_arn`"
        )
    queue_name = queue_arn.split(":")[-1]
    queue_region = queue_arn.split(":")[3]

    sqs_client = boto3.client("sqs", region_name=queue_region)

    queue_url_res = await sync_to_async(sqs_client.get_queue_url)(QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")

    messages_awaitable = await sync_to_async(sqs_client.receive_message)(
        QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    while messages:
        if num_events >= max_num_messages_to_process:
            break
        processed_messages = []
        for message in messages:
            num_events += 1
            try:
                message_body = json.loads(message["Body"])
                print("here")

                if message_body["RequestType"] != "Create":
                    log.error(
                        {
                            **log_data,
                            "error": "Unknown RequestType",
                            "cf_message": message_body,
                        }
                    )
                    processed_messages.append(
                        {
                            "Id": message["MessageId"],
                            "ReceiptHandle": message["ReceiptHandle"],
                        }
                    )
                    continue
                response_url = message_body.get("ResponseURL")
                if not response_url:
                    # We don't have a CFN response URL, so we can't respond to the request
                    # but we can make some noise in our logs
                    sentry_sdk.capture_message(
                        "Message doesn't have a response URL", "error"
                    )
                    log.error(
                        {
                            **log_data,
                            "error": "Unable to find ResponseUrl",
                            "cf_message": message_body,
                        }
                    )
                    processed_messages.append(
                        {
                            "Id": message["MessageId"],
                            "ReceiptHandle": message["ReceiptHandle"],
                        }
                    )
                    continue
                partial_stack_id_for_role = (
                    message_body["StackId"].split("/")[-1].split("-")[0]
                )
                account_id_for_role = message_body["ResourceProperties"]["AWSAccountId"]
                role_arn = f"arn:aws:iam::{account_id_for_role}:role/cloudumi-central-role-{partial_stack_id_for_role}"
                external_id = message_body["ResourceProperties"]["ExternalId"]
                host = message_body["ResourceProperties"]["Host"]

                # Verify External ID
                external_id_in_config = config.get_host_specific_key(
                    f"site_configs.{host}.tenant_details.external_id", host
                )

                if external_id != external_id_in_config:
                    sentry_sdk.capture_message(
                        "External ID from CF doesn't match host's external ID configuration",
                        "error",
                    )
                    log.error(
                        {
                            **log_data,
                            "error": "External ID Mismatch",
                            "cf_message": message_body,
                            "external_id_from_cf": external_id,
                            "external_id_in_config": external_id_in_config,
                            "host": host,
                        }
                    )
                    processed_messages.append(
                        {
                            "Id": message["MessageId"],
                            "ReceiptHandle": message["ReceiptHandle"],
                        }
                    )
                    continue

                # Assume role from noq_dev_central_role
                try:
                    sts_client = await sync_to_async(boto3_cached_conn)("sts", host)
                    await sync_to_async(sts_client.assume_role)(
                        RoleArn=role_arn,
                        RoleSessionName="noq_registration_verification",
                        ExternalId=external_id,
                    )
                except ClientError as e:
                    sentry_sdk.capture_message(
                        "Unable to assume customer's hub account role", "error"
                    )
                    log.error(
                        {
                            **log_data,
                            "message": "Unable to assume customer's hub account role",
                            "cf_message": message_body,
                            "external_id_from_cf": external_id,
                            "external_id_in_config": external_id_in_config,
                            "host": host,
                            "error": str(e),
                        }
                    )
                    processed_messages.append(
                        {
                            "Id": message["MessageId"],
                            "ReceiptHandle": message["ReceiptHandle"],
                        }
                    )
                    continue

                # Write tenant configuration to DynamoDB
                ddb = RestrictedDynamoHandler()
                host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(
                    host
                )
                if not host_config.get("account_ids_to_name"):
                    host_config["account_ids_to_name"] = {}
                host_config["account_ids_to_name"][
                    account_id_for_role
                ] = account_id_for_role
                if not host_config.get("policies"):
                    host_config["policies"] = {}
                if not host_config["policies"].get("pre_role_arns_to_assume"):
                    host_config["policies"]["pre_role_arns_to_assume"] = []
                host_config["policies"]["pre_role_arns_to_assume"].append(
                    [
                        {
                            "role_arn": role_arn,
                            "external_id": external_id,
                        }
                    ]
                )
                await ddb.update_static_config_for_host(
                    host_config, "aws_integration", host
                )

                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_iam_resources_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_s3_buckets_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_sns_topics_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_sqs_queues_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_managed_policies_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "cloudumi_common.celery_tasks.celery_tasks.cache_resources_from_aws_config_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )

                # TODO: notify user in the UI that connection was successful
                # TODO: Spawn tasks to cache resources from central account
                processed_messages.append(
                    {
                        "Id": message["MessageId"],
                        "ReceiptHandle": message["ReceiptHandle"],
                    }
                )

            except Exception as e:
                raise
        if processed_messages:
            await sync_to_async(sqs_client.delete_message_batch)(
                QueueUrl=queue_url, Entries=processed_messages
            )
        messages_awaitable = await sync_to_async(sqs_client.receive_message)(
            QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    return {"message": "Successfully processed all messages", "num_events": num_events}


# To run manually, uncomment the lines below:
# from cloudumi_common.celery_tasks.celery_tasks import app as celery_app
# async_to_sync(handle_tenant_integration_queue)(celery_app)
