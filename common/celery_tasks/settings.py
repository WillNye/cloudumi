import boto3

from common.celery_tasks import app
from common.config import config


@app.task
def synchronize_sso():
    client = boto3.client("cognito-idp", region_name=config.region)
    
