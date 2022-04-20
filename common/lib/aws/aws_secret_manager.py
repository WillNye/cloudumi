import base64

import boto3


def get_aws_secret(secret_arn):
    region = secret_arn.split(":")[3]
    # TODO: Support AWS Secrets by host
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region,
    )
    get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
    if "SecretString" in get_secret_value_response:
        return get_secret_value_response["SecretString"]
    else:
        return base64.b64decode(get_secret_value_response["SecretBinary"])
