import sys
from typing import Any, Dict, Optional

import boto3

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.github.models import GitHubInstall
from common.lib.asyncio import aio_wrapper
from common.lib.messaging import iterate_event_messages


def get_developer_queue_name() -> str:
    region = config.get("_global_.integrations.aws.region", "us-west-2")
    sts_client = boto3.client("sts", region_name=region)
    response = sts_client.get_caller_identity()
    arn = response["Arn"]
    session_name = arn.split("/")[-1]
    assert session_name.endswith("@noq.dev")
    developer_name = session_name.split("@noq.dev")[0]
    return f"local-dev-{developer_name}-github-app-webhook"


def get_developer_queue_arn() -> str:
    region = config.get("_global_.integrations.aws.region", "us-west-2")
    account_id = config.get("_global_.integrations.aws.account_id")
    queue_name = get_developer_queue_name()
    developer_queue_arn = f"arn:aws:sqs:{region}:{account_id}:{queue_name}"
    return developer_queue_arn


def allow_sns_to_write_to_sqs(topic_arn, queue_arn):
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "MyPolicy",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "SQS:SendMessage",
                "Resource": queue_arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
            }
        ],
    }
    return json.dumps(policy_document)


async def webhook_request_handler(request):
    """
    Note: this is where we wire up the control plane between webhook events and
    Noq SaaS Self Service request
    """

    body = request["body"]

    # signature is now being validated at the lambda serverless routing layer
    # because that is deployed in a separate account. we are not re-validating
    # the payload to avoid spreading the shared secret across account.
    # payload is only propagated to the SaaS post signature validation
    # see serverless/github-app-webhook-lambda.

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

    queue_arn = config.get(
        "_global_.integrations.github.webhook_event_buffer.queue_arn",
        None,
    )

    if config.is_development:
        queue_arn = get_developer_queue_arn()

    if not queue_arn and not config.is_development:
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

                # BEGIN Actual work done, the
                webhook_request = message["body"]
                await webhook_request_handler(webhook_request)
                # END special sauce, the rest is boilerplate

            except Exception:
                # Questions: what is the expected Dead Letter Queue pattern?
                raise
        if processed_messages:
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
