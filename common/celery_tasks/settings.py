import boto3
from common.config import config
from common.celery_tasks import app


@app.task
def synchronize_sso():
    client = boto3.client("cognito-idp", region_name=config.region)
    