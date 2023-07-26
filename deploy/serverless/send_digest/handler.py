import json
import os

import boto3
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def lambda_handler(event, context):
    queue_url = os.environ["QUEUE_URL"]
    email_address = os.environ["EMAIL"]
    secret_name = os.environ["SENDGRID_SECRET"]

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager")

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(get_secret_value_response["SecretString"])
    except Exception as e:
        raise e

    sendgrid_key = secret[
        "password"
    ]  # Assuming the SendGrid API Key is stored in the 'password' field of the secret
    from_email = secret["fromEmail"]

    # Create a SQS client
    sqs = boto3.client("sqs")

    # Long polling for message on the queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=["All"],
        MaxNumberOfMessages=10,
        WaitTimeSeconds=0,
    )

    # Check if the queue is empty
    if "Messages" not in response:
        print("Queue is empty")
        return

    messages = response["Messages"]
    message_bodies = [msg["Body"] for msg in messages]

    # Send email via SendGrid
    sg = SendGridAPIClient(api_key=sendgrid_key)
    message = Mail(
        from_email=from_email,
        to_emails=email_address,
        subject="New Exceptions Reported",
        plain_text_content="\n".join(message_bodies),
    )
    try:
        sg.send(message)
    except Exception as e:
        print(str(e))

    # Delete processed messages from the queue
    entries = [
        {"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]}
        for msg in messages
    ]
    sqs.delete_message_batch(QueueUrl=queue_url, Entries=entries)
