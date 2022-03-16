from common.celery_tasks import app
from common.lib.assume_role import boto3_cached_conn


@app.task
def synchronize_sso():
    client = boto3_cached_conn("cognito-idp")