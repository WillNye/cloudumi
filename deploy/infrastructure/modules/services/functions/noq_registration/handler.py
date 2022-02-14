import json
import logging
import os
from typing import Any, Dict

import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)
PHYSICAL_RESOURCE_ID = os.getenv("PHYSICAL_RESOURCE_ID", "")
REGION = os.getenv("REGION", "us-west-2")
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "259868150464")
CLUSTER_ID = os.getenv("CLUSTER_ID")


def __return(
    status: int, failure_message: str, message: Dict[str, str]
) -> Dict[str, Any]:
    logger.info(f"Returning status {status} with msg {failure_message}")
    response_url = message.get("ResponseURL")
    response_data = {
        "Status": "FAILED",
        "Reason": failure_message,
        "PhysicalResourceId": PHYSICAL_RESOURCE_ID,
        "StackId": message.get("StackId"),
        "RequestId": message.get("RequestId"),
        "LogicalResourceId": message.get("LogicalResourceId"),
    }

    response_data_json = json.dumps(response_data)
    response_header = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response_data_json)),
    }
    if response_url:
        msg = requests.put(
            response_url or "", data=json.dumps(response_data), headers=response_header
        )
    else:
        msg = {}
    return {"statusCode": status, "body": json.dumps(msg)}


def emit_s3_response(event, context):
    """Emit an S3 response to indicate successful completion of the custom resource.

    Note: the required fields to send to S3 are:
        * Status (SUCCESS/FAILED)
        * Reason (only required if Status is FAILED)
        * PhysicalResourceId
        * StackId
        * LogicalResourceId

    Ref: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html

    """
    logger.info(f"ACCOUNT_ID: {ACCOUNT_ID}")
    logger.info(f"PHYSICAL_RESOURCE_ID: {PHYSICAL_RESOURCE_ID}")
    logger.info(f"REGION: {REGION}")
    logger.info(f"CLUSTER_ID: {CLUSTER_ID}")
    sqs = boto3.client("sqs")
    if not isinstance(event, dict):
        return __return(400, "Not processing non-dict event message", {})
    if "Records" not in event:
        return __return(500, "Unexpected event - looking for Record key", {})
    if not CLUSTER_ID:
        return __return(500, "CLUSTER_ID is not defined", {})
    queue_url = sqs.get_queue_url(QueueName=f"{CLUSTER_ID}-registration-response-queue")
    if queue_url:
        queue_url = queue_url.get("QueueUrl")
    else:
        raise RuntimeError(
            f"Did not get a valid queue using {CLUSTER_ID}-registration-response-queue for the name"
        )
    records = event.get("Records", [])
    bodies = [json.loads(x.get("body", "")) for x in records]
    message_ids = [x.get("messageId") for x in records]
    receipt_handlers = [x.get("receiptHandle", "") for x in records]
    if not bodies:
        if receipt_handlers:
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handlers[0],
            )
        return __return(500, "No body sent with message", {})
    for idx, body in enumerate(bodies):
        # receipt_handles align with bodies
        logger.info(f"Handling response for SNS notification: {message_ids[idx]}")
        message = json.loads(body.get("Message"))
        response_url = message.get("ResponseURL")
        if not response_url:
            return __return(500, "Invalid response message sent from SNS", message)
        response_data = {
            "Status": "SUCCESS",
            "Reason": "OK",
            "PhysicalResourceId": PHYSICAL_RESOURCE_ID,
            "StackId": message.get("StackId"),
            "RequestId": message.get("RequestId"),
            "LogicalResourceId": message.get("LogicalResourceId"),
        }
        response_data_json = json.dumps(response_data)
        response_header = {
            "Content-Type": "application/json",
            "Content-Length": str(len(response_data_json)),
        }

        partial_stack_id_for_role = (
            message.get("StackId", "").split("/")[-1].split("-")[0]
        )
        if not partial_stack_id_for_role:
            return __return(500, "Invalid StackId sent from SNS", message)
        account_id_for_role = message.get("ResourceProperties", {}).get("AWSAccountId")
        if not account_id_for_role:
            return __return(500, "Invalid AWSAccountId sent from SNS", message)

        logger.info(f"Sending SUCCESS to {response_url}")
        requests.put(response_url, data=response_data_json, headers=response_header)
        logger.info("Deleting sqs message from queue")
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handlers[idx],
        )
    return __return(200, "OK", {})
