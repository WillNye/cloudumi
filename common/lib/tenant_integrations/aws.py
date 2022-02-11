import sys
from typing import Any, Dict, Optional

import boto3
import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest

from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.messaging import iterate_event_messages
from common.lib.yaml import yaml

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


async def get_central_role_arn(host):
    """
    Get the ARN of the central role for the given host.
    """
    # Get the central role ARN
    pre_role_arns_to_assume = config.get_host_specific_key(
        "policies.pre_role_arns_to_assume", host, []
    )
    if pre_role_arns_to_assume:
        return pre_role_arns_to_assume[-1]["role_arn"]
    return None


async def handle_spoke_account_registration(body):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }
    spoke_role_name = body["ResourceProperties"]["SpokeRole"]
    account_id_for_role = body["ResourceProperties"]["AWSAccountId"]
    spoke_role_arn = f"arn:aws:iam::{account_id_for_role}:role/{spoke_role_name}"
    host = body["ResourceProperties"]["Host"]

    external_id = config.get_host_specific_key("tenant_details.external_id", host)
    # Get central role arn
    central_role_arn = await get_central_role_arn(host)
    if not central_role_arn:
        raise Exception("No Central Role ARN detected in configuration.")

    # Assume role from noq_dev_central_role
    try:
        sts_client = await sync_to_async(boto3_cached_conn)("sts", host)
        central_role_credentials = await sync_to_async(sts_client.assume_role)(
            RoleArn=central_role_arn,
            RoleSessionName="noq_registration_verification",
            ExternalId=external_id,
        )
    except ClientError as e:
        sentry_sdk.capture_message(
            "Unable to assume customer's central account role", "error"
        )
        log.error(
            {
                **log_data,
                "message": "Unable to assume customer's hub account role",
                "cf_message": body,
                "external_id": external_id,
                "host": host,
                "error": str(e),
            }
        )
        return False

    customer_central_role_sts_client = await sync_to_async(boto3.client)(
        "sts",
        aws_access_key_id=central_role_credentials["Credentials"]["AccessKeyId"],
        aws_secret_access_key=central_role_credentials["Credentials"][
            "SecretAccessKey"
        ],
        aws_session_token=central_role_credentials["Credentials"]["SessionToken"],
    )

    try:
        customer_spoke_role_credentials = await sync_to_async(
            customer_central_role_sts_client.assume_role
        )(
            RoleArn=spoke_role_arn,
            RoleSessionName="noq_registration_verification",
        )
    except ClientError as e:
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": "Unable to assume customer's spoke account role",
                "cf_message": body,
                "external_id": external_id,
                "host": host,
                "error": str(e),
            }
        )
        return False

    customer_spoke_role_iam_client = await sync_to_async(boto3.client)(
        "iam",
        aws_access_key_id=customer_spoke_role_credentials["Credentials"]["AccessKeyId"],
        aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
            "SecretAccessKey"
        ],
        aws_session_token=customer_spoke_role_credentials["Credentials"][
            "SessionToken"
        ],
    )

    account_aliases_co = await sync_to_async(
        customer_spoke_role_iam_client.list_account_aliases
    )()
    account_aliases = account_aliases_co["AccountAliases"]
    if account_aliases:
        account_name = account_aliases[0]
    else:
        account_name = account_id_for_role

    # Write tenant configuration to DynamoDB
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)
    if not host_config.get("account_ids_to_name"):
        host_config["account_ids_to_name"] = {}
    host_config["account_ids_to_name"][account_id_for_role] = account_name
    if not host_config.get("policies"):
        host_config["policies"] = {}
    if not host_config["policies"].get("role_name"):
        host_config["policies"]["role_name"] = spoke_role_name

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), "aws_integration", host
    )
    return True


async def handle_central_account_registration(body):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }
    spoke_role_name = body["ResourceProperties"]["SpokeRole"]
    account_id_for_role = body["ResourceProperties"]["AWSAccountId"]
    role_arn = body["ResourceProperties"]["ClusterRoleArn"]
    external_id = body["ResourceProperties"]["ExternalId"]
    host = body["ResourceProperties"]["Host"]

    # Verify External ID
    external_id_in_config = config.get_host_specific_key(
        "tenant_details.external_id", host
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
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
            }
        )
        return False

    # Assume role from noq_dev_central_role
    try:
        sts_client = boto3.client("sts")
        customer_central_account_creds = await sync_to_async(sts_client.assume_role)(
            RoleArn=role_arn,
            RoleSessionName="noq_registration_verification",
            ExternalId=external_id,
        )
    except ClientError as e:
        sentry_sdk.capture_message(
            "Unable to assume customer's central account role", "error"
        )
        log.error(
            {
                **log_data,
                "message": "Unable to assume customer's hub account role",
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
                "error": str(e),
            }
        )
        return False

    try:
        central_account_sts_client = await sync_to_async(boto3.client)(
            "sts",
            aws_access_key_id=customer_central_account_creds["Credentials"][
                "AccessKeyId"
            ],
            aws_secret_access_key=customer_central_account_creds["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=customer_central_account_creds["Credentials"][
                "SessionToken"
            ],
        )
        central_account_sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{account_id_for_role}:role/{spoke_role_name}",
            RoleSessionName="noq_registration_verification",
        )
    except ClientError as e:
        sentry_sdk.capture_message(
            "Unable to assume customer's spoke account role", "error"
        )
        log.error(
            {
                **log_data,
                "message": "Unable to assume customer's spoke account role",
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
                "error": str(e),
            }
        )
        return False

    # Write tenant configuration to DynamoDB
    ddb = RestrictedDynamoHandler()
    host_config = await sync_to_async(ddb.get_static_config_for_host_sync)(host)
    if not host_config.get("account_ids_to_name"):
        host_config["account_ids_to_name"] = {}
    host_config["account_ids_to_name"][account_id_for_role] = account_id_for_role
    if not host_config.get("policies"):
        host_config["policies"] = {}
    if not host_config["policies"].get("pre_role_arns_to_assume"):
        host_config["policies"]["pre_role_arns_to_assume"] = []
    host_config["policies"]["pre_role_arns_to_assume"] = [
        {
            "role_arn": role_arn,
            "external_id": external_id,
        }
    ]
    host_config["policies"]["role_name"] = spoke_role_name
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), "aws_integration", host
    )
    config.CONFIG.copy_tenant_config_dynamo_to_redis(host)
    return True


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

    account_id = config.get("_global_.integrations.aws.account_id")
    cluster_id = config.get("_global_.deployment.cluster_id")
    region = config.get("_global_.integrations.aws.region")
    queue_arn = config.get(
        "_global_.integrations.aws.registration_queue_arn",
        f"arn:aws:sqs:{region}:{account_id}:{cluster_id}-registration-queue",
    )
    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`_global_.integrations.aws.registration_queue_arn`"
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

        for message in iterate_event_messages(queue_region, queue_name, messages):
            num_events += 1
            try:
                message_id = message.get("message_id")
                receipt_handle = message.get("receipt_handle")
                processed_messages.append(
                    {
                        "Id": message_id,
                        "ReceiptHandle": receipt_handle,
                    }
                )

                if message["body"]["RequestType"] != "Create":
                    log_data[
                        "message"
                    ] = f"RequestType {message['body']['RequestType']} not supported"
                    log.debug(log_data)
                    continue
                action_type = message["body"]["ResourceProperties"]["ActionType"]
                if action_type not in [
                    "AWSSpokeAcctRegistration",
                    "AWSCentralAcctRegistration",
                ]:
                    log_data["message"] = f"ActionType {action_type} not supported"
                    log.debug(log_data)
                    continue
                body = message.get("body")
                # TODO: Handle all request types. Valid request types: Create, Update, Delete
                if body.get("RequestType") != "Create":
                    log.error(
                        {
                            **log_data,
                            "error": "Unknown RequestType",
                            "cf_message": body,
                        }
                    )
                    continue

                response_url = body.get("ResponseURL")
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
                            "cf_message": body,
                        }
                    )
                    continue

                if action_type == "AWSSpokeAcctRegistration":
                    await handle_spoke_account_registration(body)
                elif action_type == "AWSCentralAcctRegistration":
                    await handle_central_account_registration(body)
                # TODO: Refresh configuration
                # Ensure it is written to Redis. trigger refresh job in worker

                host = body["ResourceProperties"]["Host"]
                account_id_for_role = body["ResourceProperties"]["AWSAccountId"]
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_iam_resources_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_s3_buckets_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_sns_topics_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_sqs_queues_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_managed_policies_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )
                celery_app.send_task(
                    "common.celery_tasks.celery_tasks.cache_resources_from_aws_config_for_account",
                    args=[account_id_for_role],
                    kwargs={"host": host},
                )

            except Exception:
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
