import json
import logging
from typing import Dict

import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
PHYSICAL_RESOURCE_ID = "f4b52b3d-0056-4ec0-aca4-ac61ed2efd1d"


def __return(status: int, failure_message: str, message: Dict[str, str]):
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
    msg = requests.put(
        response_url, data=json.dumps(response_data), headers=response_header
    )
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
    sqs = boto3.client("sqs")
    if not isinstance(event, dict):
        return __return(400, "Not processing non-dict event message")
    if not "Records" in event:
        return __return(500, "Unexpected event - looking for Record key")
    records = event.get("Records", [])
    bodies = [json.loads(x.get("body", "")) for x in records]
    message_ids = [x.get("messageId") for x in records]
    receipt_handlers = [x.get("receiptHandle", "") for x in records]
    if not bodies:
        if receipt_handlers:
            sqs.delete_message(
                QueueUrl="https://sqs.us-east-1.amazonaws.com/259868150464/noq_registration_response_queue",
                ReceiptHandle=receipt_handlers[0],
            )
        return __return(500, "No body sent with message")
    for idx, body in enumerate(bodies):
        # receipt_handles align with bodies
        logger.info(f"Handling response for SNS notification: {message_ids[idx]}")
        message = json.loads(body.get("Message"))
        response_url = message.get("ResponseURL")
        if not response_url:
            return __return(500, "Invalid response message sent from SNS")
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
        role_arn = f"arn:aws:iam::{account_id_for_role}:role/cloudumi-central-role-{partial_stack_id_for_role}"
        # TODO: Validate External ID
        # TODO: Try to assume IAM role from cluster role ARN
        # TODO: Put Role ARN in DynamoDB Table
        ddb = boto3.client("dynamodb")
        ddb.put_item(
            TableName="cloudumi-central-role-arn-table",
            Item={
                "StackId": {"S": message.get("StackId")},
                "RoleArn": {"S": role_arn},
                "PhysicalResourceId": {"S": PHYSICAL_RESOURCE_ID},
            },
        )

        logger.info(f"Sending SUCCESS to {response_url}")
        requests.put(response_url, data=response_data_json, headers=response_header)
        logger.info(f"Deleting sqs message from queue")
        sqs.delete_message(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/259868150464/noq_registration_response_queue",
            ReceiptHandle=receipt_handlers[idx],
        )
    return __return(200, "OK")
