import json
import os

import boto3

sns = boto3.client("sns")
topic_arn = os.environ["topic_arn"]


def lambda_handler(event, context):
    # print(event)

    # TODO: shall we implement signature verification
    # here to cut down DDoS possibilities.

    # TODO: need a really fast implementation to translate
    # installation_id to topic_arn. it's difficult to use
    # message filter policy likely due to maximum size of
    # policy

    _ = sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(event),
        Subject="github",
        MessageStructure="string",
    )

    return {"statusCode": 200, "body": json.dumps("Stash to queue")}
