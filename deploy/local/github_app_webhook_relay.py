import boto3
import httpx

import common.lib.noq_json as json

queue_url = (
    "https://sqs.us-west-2.amazonaws.com/759357822767/github-app-noq-dev-webhook-buffer"
)
local_tunnel_host = "noq-steven.loca.lt"


def consume_messages(client):

    # Receive message from SQS queue
    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        VisibilityTimeout=0,
        WaitTimeSeconds=20,
    )

    if "Messages" not in response:
        return

    message = response["Messages"][0]
    receipt_handle = message["ReceiptHandle"]

    # does the relay
    event = json.loads(message["Body"])
    headers = {}
    headers["x-hub-signature-256"] = event["headers"]["x-hub-signature-256"]
    headers["content-type"] = event["headers"]["content-type"]

    response = httpx.post(
        f"https://{local_tunnel_host}/api/v3/github/events/",
        headers=headers,
        content=event["body"].encode("utf-8"),
        timeout=100,
    )
    response.raise_for_status()

    # Delete received message from queue
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


if __name__ == "__main__":
    sqs_client = boto3.client("sqs", region_name="us-west-2")
    while True:
        consume_messages(sqs_client)
