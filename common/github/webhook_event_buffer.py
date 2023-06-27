import sys
from typing import Any, Dict, Optional

import boto3

import common.lib.noq_json as json
from api.handlers.v3.github.handler import verify_signature
from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.github.models import GitHubInstall
from common.lib.asyncio import aio_wrapper
from common.lib.messaging import iterate_event_messages


async def webhook_request_handler(request):

    headers = request["headers"]
    body = request["body"]

    # the format is in sha256=<sig>
    request_signature = headers["x-hub-signature-256"].split("=")[1]
    # because this handler is unauthenticated, always verify signature before taking action
    verify_signature(request_signature, body)
    github_event = json.loads(body)
    github_installation_id = github_event["installation"]["id"]

    tenant_github_install = await GitHubInstall.get_with_installation_id(
        github_installation_id
    )
    if not tenant_github_install:
        # What's the right handling?
        # raise HTTPError(400, "Unknown installation id")
        # FIXME
        pass

    github_action = github_event["action"]
    if github_action == "deleted":
        await tenant_github_install.delete()
        return


async def handle_github_webhook_event_queue(
    celery_app,
    max_num_messages_to_process: Optional[int] = None,
) -> Dict[str, Any]:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }
    assert log_data

    if not max_num_messages_to_process:
        max_num_messages_to_process = config.get(
            "_global_.integrations.github.webhook_event_buffer.max_num_messages_to_process",
            100,
        )

    account_id = config.get("_global_.integrations.aws.account_id")
    cluster_id = config.get("_global_.deployment.cluster_id")
    region = config.get("_global_.integrations.aws.region")
    queue_arn = config.get(
        "_global_.integrations.github.webhook_event_buffer.queue_arn",
        f"arn:aws:sqs:{region}:{account_id}:{cluster_id}-github-app-webhook-buffer",
    )
    if not queue_arn:
        raise MissingConfigurationValue(
            "Unable to find required configuration value: "
            "`_global_.integrations.github.webhook_event_buffer.queue_arn`"
        )
    queue_name = queue_arn.split(":")[-1]
    queue_region = queue_arn.split(":")[3]

    sqs_client = boto3.client("sqs", region_name=queue_region)

    queue_url_res = await aio_wrapper(sqs_client.get_queue_url, QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")

    messages_awaitable = await aio_wrapper(
        sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
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

                webhook_request = message["body"]
                await webhook_request_handler(webhook_request)

                # action_type = message["body"]["ResourceProperties"]["ActionType"]
                # if action_type not in [
                #     "AWSSpokeAcctRegistration",
                #     "AWSCentralAcctRegistration",
                # ]:
                #     log_data["message"] = f"ActionType {action_type} not supported"
                #     log.debug(log_data)
                #     continue

                # body = message.get("body", {})
                # request_type = body.get("RequestType")
                # response_url = body.get("ResponseURL")
                # resource_properties = body.get("ResourceProperties", {})
                # tenant = resource_properties.get("Host")
                # external_id = resource_properties.get("ExternalId")
                # physical_resource_id = external_id
                # stack_id = body.get("StackId")
                # request_id = body.get("RequestId")
                # logical_resource_id = body.get("LogicalResourceId")

                # if not (
                #     body
                #     or physical_resource_id
                #     or response_url
                #     or tenant
                #     or external_id
                #     or resource_properties
                #     or stack_id
                #     or request_id
                #     or logical_resource_id
                # ):
                #     # We don't have a CFN Physical Resource ID, so we can't respond to the request
                #     # but we can make some noise in our logs
                #     error_mesage = "SQS message doesn't have expected parameters"
                #     sentry_sdk.capture_message(error_mesage, "error")
                #     log.error(
                #         {
                #             **log_data,
                #             "error": error_mesage,
                #             "cf_message": body,
                #             "physical_resource_id": physical_resource_id,
                #             "response_url": response_url,
                #             "tenant": tenant,
                #             "external_id": external_id,
                #             "resource_properties": resource_properties,
                #             "stack_id": stack_id,
                #             "request_id": request_id,
                #         }
                #     )
                #     # There's no way to respond without some parameters
                #     if (
                #         response_url
                #         and physical_resource_id
                #         and stack_id
                #         and request_id
                #         and logical_resource_id
                #         and tenant
                #     ):
                #         await return_cf_response(
                #             "SUCCESS",
                #             "OK",
                #             response_url,
                #             physical_resource_id,
                #             stack_id,
                #             request_id,
                #             logical_resource_id,
                #             tenant,
                #         )
                #     continue

                # if request_type not in ["Create", "Update", "Delete"]:
                #     log.error(
                #         {
                #             **log_data,
                #             "error": "Unknown RequestType",
                #             "cf_message": body,
                #             "request_type": request_type,
                #         }
                #     )
                #     await return_cf_response(
                #         "FAILED",
                #         "Unknown Request Type",
                #         response_url,
                #         physical_resource_id,
                #         stack_id,
                #         request_id,
                #         logical_resource_id,
                #         tenant,
                #     )
                #     continue

                # if request_type in ["Update", "Delete"]:
                #     # Send success message to CloudFormation
                #     await return_cf_response(
                #         "SUCCESS",
                #         "OK",
                #         response_url,
                #         physical_resource_id,
                #         stack_id,
                #         request_id,
                #         logical_resource_id,
                #         tenant,
                #     )
                #     # TODO: Handle deletion in Noq. It's okay if this is manual for now.
                #     continue

                # if action_type == "AWSSpokeAcctRegistration":
                #     res = await handle_spoke_account_registration(body)
                # elif action_type == "AWSCentralAcctRegistration":
                #     res = await handle_central_account_registration(body)
                # else:
                #     error_message = "ActionType not supported"
                #     log.error(
                #         {
                #             **log_data,
                #             "error": error_message,
                #             "cf_message": body,
                #             "request_type": request_type,
                #             "action_type": action_type,
                #             "physical_resource_id": physical_resource_id,
                #             "response_url": response_url,
                #             "tenant": tenant,
                #             "external_id": external_id,
                #             "resource_properties": resource_properties,
                #             "stack_id": stack_id,
                #             "request_id": request_id,
                #         }
                #     )
                #     sentry_sdk.capture_message(error_message, "error")
                #     await return_cf_response(
                #         "FAILED",
                #         error_message,
                #         response_url,
                #         physical_resource_id,
                #         stack_id,
                #         request_id,
                #         logical_resource_id,
                #         tenant,
                #     )
                #     continue

                # if res["success"]:
                #     await return_cf_response(
                #         "SUCCESS",
                #         "OK",
                #         response_url,
                #         physical_resource_id,
                #         stack_id,
                #         request_id,
                #         logical_resource_id,
                #         tenant,
                #     )
                # else:
                #     await return_cf_response(
                #         "FAILED",
                #         res["message"],
                #         response_url,
                #         physical_resource_id,
                #         stack_id,
                #         request_id,
                #         logical_resource_id,
                #         tenant,
                #     )
                #     continue
                # # TODO: Refresh configuration
                # # Ensure it is written to Redis. trigger refresh job in worker

                # account_id_for_role = body["ResourceProperties"]["AWSAccountId"]
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_iam_resources_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_s3_buckets_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_sns_topics_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_sqs_queues_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_managed_policies_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_resources_from_aws_config_for_account",
                #     args=[account_id_for_role],
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_self_service_typeahead_task",
                #     kwargs={"tenant": tenant},
                #     countdown=120,
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_organization_structure",
                #     kwargs={"tenant": tenant},
                # )
                # celery_app.send_task(
                #     "common.celery_tasks.celery_tasks.cache_scps_across_organizations",
                #     kwargs={"tenant": tenant},
                #     countdown=120,
                # )

            except Exception:
                # Questions: what is the expected Dead Letter Queue pattern?
                raise
        if processed_messages:
            # FIXME: temporary skip out delete messages during debugging
            pass
            await aio_wrapper(
                sqs_client.delete_message_batch,
                QueueUrl=queue_url,
                Entries=processed_messages,
            )
        messages_awaitable = await aio_wrapper(
            sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    return {"message": "Successfully processed all messages", "num_events": num_events}
