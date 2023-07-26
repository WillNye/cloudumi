import json
import os

import boto3


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    sqs = boto3.client("sqs")
    bucket_name = os.environ["BUCKET_NAME"]
    queue_url = os.environ["QUEUE_URL"]

    # Extract the report from the event
    report = event["body"]

    # Generate a unique filename for the report
    filename = f"report-{context.aws_request_id}.txt"

    # Write the report to the S3 bucket
    s3.put_object(Body=report, Bucket=bucket_name, Key=filename)
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({"bucket": bucket_name, "filename": filename}),
    )
    return {"statusCode": 200, "body": "Report received successfully!"}
