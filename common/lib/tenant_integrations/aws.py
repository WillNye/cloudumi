import sys
from typing import Any, Dict, Optional

import boto3
import sentry_sdk
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest

from common.config import config
from common.config.account import get_hub_account, set_hub_account, upsert_spoke_account
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.messaging import iterate_event_messages

log = config.get_logger()


async def return_cf_response(
    status: str,
    status_message: Optional[str],
    response_url: str,
    physical_resource_id: str,
    stack_id: str,
    request_id: str,
    logical_resource_id: str,
    host: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Emit an S3 error event to CloudFormation.
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "status": status,
        "status_message": status_message,
        "host": host,
        "physical_resource_id": physical_resource_id,
        "message": "Responding to CloudFormation",
    }

    http_client = AsyncHTTPClient(force_instance=True)

    response_data = {
        "Status": status,
        "Reason": status_message,
        "PhysicalResourceId": physical_resource_id,
        "StackId": stack_id,
        "RequestId": request_id,
        "LogicalResourceId": logical_resource_id,
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
        log_data["message"] = "Notification sent"
        log_data["response_body"] = resp.body
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending notification to CF"
        log_data["error"] = str(e)
        log.error(log_data)
        sentry_sdk.capture_exception()
        return {"statusCode": status, "body": None}

    return {"statusCode": status, "body": resp.body}


async def handle_spoke_account_registration(body):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }

    spoke_role_name = body["ResourceProperties"].get("SpokeRoleName")
    account_id_for_role = body["ResourceProperties"].get("AWSAccountId")
    host = body["ResourceProperties"].get("Host")
    external_id = body["ResourceProperties"].get("ExternalId")
    if not spoke_role_name or not account_id_for_role or not external_id or not host:
        error_message = (
            "Message is missing spoke_role_name, account_id_for_role, or host"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "spoke_role_name": spoke_role_name,
                "account_id_for_role": account_id_for_role,
                "host": host,
                "external_id": external_id,
            }
        )
        return (
            {
                "success": False,
                "message": error_message,
            },
        )

    # Verify External ID
    external_id_in_config = config.get_host_specific_key(
        "tenant_details.external_id", host
    )

    if external_id != external_id_in_config:
        error_message = (
            "External ID from CF doesn't match host's external ID configuration"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
            }
        )
        return (
            {
                "success": False,
                "message": error_message,
            },
        )

    spoke_role_arn = f"arn:aws:iam::{account_id_for_role}:role/{spoke_role_name}"

    external_id = config.get_host_specific_key("tenant_details.external_id", host)
    # Get central role arn
    hub_account = await get_hub_account(host)
    central_role_arn = hub_account.get("role_arn")
    if not central_role_arn:
        error_message = "No Central Role ARN detected in configuration."
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
            }
        )
        return (
            {
                "success": False,
                "message": error_message,
            },
        )

    # Assume role from noq_dev_central_role
    try:
        sts_client = await sync_to_async(boto3_cached_conn)("sts", host)
        central_role_credentials = await sync_to_async(sts_client.assume_role)(
            RoleArn=central_role_arn,
            RoleSessionName="noq_registration_verification",
            ExternalId=external_id,
        )
    except ClientError as e:
        error_message = "Unable to assume customer's central account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id": external_id,
                "host": host,
                "error": str(e),
            }
        )
        return (
            {
                "success": False,
                "message": error_message,
            },
        )

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
        error_message = "Unable to assume customer's spoke account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id": external_id,
                "host": host,
                "error": str(e),
            }
        )
        return (
            {
                "success": False,
                "message": error_message,
            },
        )

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
    master_account = True
    if account_aliases:
        account_name = account_aliases[0]
        master_account = False
    else:
        account_name = account_id_for_role
        # Try Organizations
        customer_spoke_role_org_client = await sync_to_async(boto3.client)(
            "organizations",
            aws_access_key_id=customer_spoke_role_credentials["Credentials"][
                "AccessKeyId"
            ],
            aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=customer_spoke_role_credentials["Credentials"][
                "SessionToken"
            ],
        )
        try:
            account_details_call = await sync_to_async(
                customer_spoke_role_org_client.describe_account
            )(AccountId=account_id_for_role)
            account_details = account_details_call.get("Account")
            if account_details and account_details.get("Name"):
                account_name = account_details["Name"]
        except ClientError:
            # Most likely this isn't an organizations master account and we can ignore
            master_account = False

    await upsert_spoke_account(
        host,
        account_name,
        account_id_for_role,
        spoke_role_name,
        external_id,
        central_role_arn,
        master_account,
    )
    return {
        "success": True,
        "message": "Successfully registered spoke account",
    }


async def handle_central_account_registration(body) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }

    log.info(f"ResourceProperties: {body['ResourceProperties']}")

    spoke_role_name = body["ResourceProperties"].get("SpokeRole")
    account_id_for_role = body["ResourceProperties"].get("AWSAccountId")
    role_arn = body["ResourceProperties"].get("CentralRoleArn")
    external_id = body["ResourceProperties"].get("ExternalId")
    host = body["ResourceProperties"].get("Host")

    if (
        not spoke_role_name
        or not account_id_for_role
        or not role_arn
        or not external_id
        or not host
    ):
        error_message = "Missing spoke_role_name, account_id_for_role, role_arn, external_id, or host in message body"
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "spoke_role_name": spoke_role_name,
                "account_id_for_role": account_id_for_role,
                "role_arn": role_arn,
                "external_id": external_id,
                "host": host,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    # Verify External ID
    external_id_in_config = config.get_host_specific_key(
        "tenant_details.external_id", host
    )

    if external_id != external_id_in_config:
        error_message = (
            "External ID from CF doesn't match host's external ID configuration"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    # Assume role from noq_dev_central_role
    try:
        sts_client = boto3.client("sts")
        customer_central_account_creds = await sync_to_async(sts_client.assume_role)(
            RoleArn=role_arn,
            RoleSessionName="noq_registration_verification",
            ExternalId=external_id,
        )
    except ClientError as e:
        error_message = "Unable to assume customer's central account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

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
        error_message = "Unable to assume customer's spoke account role"
        sentry_sdk.capture_message(error_message, "error")
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "host": host,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    await set_hub_account(
        host, "_hub_account_", account_id_for_role, role_arn, external_id
    )
    await upsert_spoke_account(
        host,
        spoke_role_name,
        account_id_for_role,
        spoke_role_name,
        external_id,
        role_arn,
    )
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

                # TODO: handle deletion / updates
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

                body = message.get("body", {})
                request_type = body.get("RequestType")
                response_url = body.get("ResponseURL")
                resource_properties = body.get("ResourceProperties", {})
                host = resource_properties.get("Host")
                external_id = resource_properties.get("ExternalId")
                physical_resource_id = external_id
                stack_id = body.get("StackId")
                request_id = body.get("RequestId")
                logical_resource_id = body.get("LogicalResourceId")

                if not (
                    body
                    or physical_resource_id
                    or response_url
                    or host
                    or external_id
                    or resource_properties
                    or stack_id
                    or request_id
                    or logical_resource_id
                ):
                    # We don't have a CFN Physical Resource ID, so we can't respond to the request
                    # but we can make some noise in our logs
                    error_mesage = "SQS message doesn't have expected parameters"
                    sentry_sdk.capture_message(error_mesage, "error")
                    log.error(
                        {
                            **log_data,
                            "error": error_mesage,
                            "cf_message": body,
                            "physical_resource_id": physical_resource_id,
                            "response_url": response_url,
                            "host": host,
                            "external_id": external_id,
                            "resource_properties": resource_properties,
                            "stack_id": stack_id,
                            "request_id": request_id,
                        }
                    )
                    # There's no way to respond without some parameters
                    if (
                        response_url
                        and physical_resource_id
                        and stack_id
                        and request_id
                        and logical_resource_id
                        and host
                    ):
                        await return_cf_response(
                            "SUCCESS",
                            "OK",
                            response_url,
                            physical_resource_id,
                            stack_id,
                            request_id,
                            logical_resource_id,
                            host,
                        )
                    continue

                if request_type not in ["Create", "Delete"]:
                    log.error(
                        {
                            **log_data,
                            "error": "Unknown RequestType",
                            "cf_message": body,
                            "request_type": request_type,
                        }
                    )
                    if request_type == "Update":
                        await return_cf_response(
                            "SUCCESS",
                            "OK",
                            response_url,
                            physical_resource_id,
                            stack_id,
                            request_id,
                            logical_resource_id,
                            host,
                        )
                    else:
                        await return_cf_response(
                            "FAILED",
                            "Unknown Request Type",
                            response_url,
                            physical_resource_id,
                            stack_id,
                            request_id,
                            logical_resource_id,
                            host,
                        )
                    continue

                if request_type == "Delete":
                    # Send success message to CloudFormation
                    await return_cf_response(
                        "SUCCESS",
                        "OK",
                        response_url,
                        physical_resource_id,
                        stack_id,
                        request_id,
                        logical_resource_id,
                        host,
                    )
                    # TODO: Handle deletion in Noq. It's okay if this is manual for now.
                    continue

                if action_type == "AWSSpokeAcctRegistration":
                    res = await handle_spoke_account_registration(body)
                elif action_type == "AWSCentralAcctRegistration":
                    res = await handle_central_account_registration(body)
                else:
                    error_message = "ActionType not supported"
                    log.error(
                        {
                            **log_data,
                            "error": error_message,
                            "cf_message": body,
                            "request_type": request_type,
                            "action_type": action_type,
                            "physical_resource_id": physical_resource_id,
                            "response_url": response_url,
                            "host": host,
                            "external_id": external_id,
                            "resource_properties": resource_properties,
                            "stack_id": stack_id,
                            "request_id": request_id,
                        }
                    )
                    sentry_sdk.capture_message(error_message, "error")
                    await return_cf_response(
                        "FAILED",
                        error_message,
                        response_url,
                        physical_resource_id,
                        stack_id,
                        request_id,
                        logical_resource_id,
                        host,
                    )
                    continue

                if res["success"]:
                    await return_cf_response(
                        "SUCCESS",
                        "OK",
                        response_url,
                        physical_resource_id,
                        stack_id,
                        request_id,
                        logical_resource_id,
                        host,
                    )
                else:
                    await return_cf_response(
                        "FAILED",
                        res["message"],
                        response_url,
                        physical_resource_id,
                        stack_id,
                        request_id,
                        logical_resource_id,
                        host,
                    )
                    continue
                # TODO: Refresh configuration
                # Ensure it is written to Redis. trigger refresh job in worker

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
