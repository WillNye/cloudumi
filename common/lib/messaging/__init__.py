import json
import logging
from typing import Dict, Generator, List

import boto3

logger = logging.getLogger(__name__)


def __get_queue_name_from_arn(event_source_arn: str) -> str:
    """Return the name of the queue, given an arn"""
    return event_source_arn.split(":")[-1]


def delete_msg_on_sqs(region: str, receipt_handle: str, event_source_arn: str) -> dict:
    client = boto3.client("sqs", region_name=region)
    response = client.get_queue_url(
        QueueName=__get_queue_name_from_arn(event_source_arn)
    )
    queue_url = response.get("QueueUrl")
    response = client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    return response


def __build_event_message(
    message_id: str, receipt_handle: str, queue_arn: str, body: dict
) -> dict:
    return {
        "message_id": message_id,
        "receipt_handle": receipt_handle,
        "queue_arn": queue_arn,
        "body": body,
    }


def __is_payload_subscription_notification(payload: dict) -> bool:
    return payload.get("Type") == "Notification"


def __extract_subscription_notification_message_body(payload: dict) -> dict:
    return json.loads(payload.get("Message", ""))


def iterate_event_messages(
    region: str, queue_name: str, messages: List[Dict[str, str]]
) -> Generator[dict, None, None]:
    """Return iterator of messages with the following structure:
    - message_id
    - receipt handle
    - queue_arn
    - body

    Handles SQS events or SNS -> SQS subscription notification events the same
    """
    client = boto3.client("sqs", region_name=region)
    resp = client.get_queue_url(QueueName=queue_name)
    queue_url = resp.get("QueueUrl")
    if not queue_url:
        raise RuntimeError(f"Invalid queue name: {queue_name}")
    resp = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])
    queue_arn = resp.get("Attributes", {}).get("QueueArn")

    for message in messages:
        receipt_handle = message.get("ReceiptHandle")
        if not receipt_handle:
            raise RuntimeError(
                f"Non-standard event message, does not have a b|ReceiptHandle: {message}"
            )
        message_id = message.get("MessageId", "unset")
        body = json.loads(message.get("Body", "{}"))
        if not body:
            raise RuntimeError(
                f"Non-standard event message, does not have a b|Body: {message}"
            )
        if __is_payload_subscription_notification(body):
            body = __extract_subscription_notification_message_body(body)
        yield __build_event_message(message_id, receipt_handle, queue_arn, body)


def publish_msg_to_sns_via_topic_arn(region: str, arn: str, msg: dict) -> dict:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sns.html#SNS.Client.publish
    client = boto3.client("sns", region_name=region)
    json_msg = json.dumps(msg)
    response = client.publish(
        TargetArn=arn,
        Message=json.dumps({"default": json_msg}),
        MessageStructure="json",
    )
    return response


def publish_msg_sns_name(region: str, name: str, msg: dict) -> dict:
    client = boto3.client("sns", region_name=region)
    resp = client.create_topic(Name=name)
    topic_arn = resp.get("TopicArn")
    return publish_msg_to_sns_via_topic_arn(region, topic_arn, msg)


def publish_msg_sqs_name(
    region: str, queue_name: str, msg: dict, delay: int = 0
) -> dict:
    client = boto3.client("sqs", region_name=region)
    response = client.get_queue_url(QueueName=queue_name)
    queue_url = response.get("QueueUrl")
    json_msg = json.dumps(msg)
    response = client.send_message(
        QueueUrl=queue_url, MessageBody=json_msg, DelaySeconds=delay
    )
    return response
