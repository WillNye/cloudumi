import os
import pathlib
import time

import boto3
import yaml
from botocore.exceptions import ClientError

current_path = pathlib.Path(__file__).parent.resolve()

task_definition_yaml_f = f"{current_path}/task_definition.yaml"
cluster_name = "staging-noq-dev-shared-staging-1"
service_name = "staging-noq-dev-shared-staging-1"
subnets = ["subnet-0dd8e008f770bd447", "subnet-0ae657185cbb32ee3"]
security_groups = ["sg-0344d82e7000960df"]
os.environ["AWS_PROFILE"] = "noq_staging"
region = "us-west-2"
account_id = "259868150464"
kms_key_arn = (
    "arn:aws:kms:us-west-2:259868150464:key/c772a276-6f4d-455b-a2fc-99681435401e"
)
noq_ecs_log_group_name = "staging-noq-dev-shared-staging-1-ecs"

with open(task_definition_yaml_f, "r") as f:
    task_definition = yaml.load(f, Loader=yaml.FullLoader)

ecr_client = boto3.client("ecr", region_name=region)
response = ecr_client.get_authorization_token(
    registryIds=[
        account_id,
    ]
)

ecs_client = boto3.client("ecs", region_name=region)

try:
    ecs_client.create_cluster(
        clusterName=cluster_name,
        configuration={
            "executeCommandConfiguration": {
                "kmsKeyId": kms_key_arn,
                "logging": "OVERRIDE",
                "logConfiguration": {
                    "cloudWatchLogGroupName": noq_ecs_log_group_name,
                    "cloudWatchEncryptionEnabled": True,
                },
            }
        },
    )
except ClientError as e:
    if not e.response["Error"] == {
        "Message": "Arguments on this idempotent request are inconsistent with arguments used in previous request(s).",
        "Code": "InvalidParameterException",
    }:
        raise
    ecs_client.update_cluster(
        cluster=cluster_name,
        configuration={
            "executeCommandConfiguration": {
                "kmsKeyId": kms_key_arn,
                "logging": "OVERRIDE",
                "logConfiguration": {
                    "cloudWatchLogGroupName": noq_ecs_log_group_name,
                    "cloudWatchEncryptionEnabled": True,
                },
            }
        },
    )

registered_task_definition = ecs_client.register_task_definition(**task_definition)

task_definition_name = "{}:{}".format(
    registered_task_definition["taskDefinition"]["family"],
    registered_task_definition["taskDefinition"]["revision"],
)

try:
    service = ecs_client.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=task_definition_name,
        desiredCount=1,
        launchType="FARGATE",
        enableExecuteCommand=True,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "assignPublicIp": "DISABLED",
                "securityGroups": security_groups,
            }
        },
    )
except ClientError as e:
    if e.response["Error"] != {
        "Message": "Creation of service was not idempotent.",
        "Code": "InvalidParameterException",
    }:
        raise
    service = ecs_client.update_service(
        cluster=cluster_name,
        service=service_name,
        taskDefinition=task_definition_name,
        desiredCount=1,
        enableExecuteCommand=True,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": subnets,
                "assignPublicIp": "DISABLED",
                "securityGroups": security_groups,
            }
        },
    )

while True:
    service_status = ecs_client.describe_services(
        cluster=cluster_name, services=[service_name]
    )
    rollout_finalized = False
    for service in service_status["services"]:
        for deployment in service["deployments"]:
            if deployment["status"] == "PRIMARY":
                print(
                    "Service: {}, Pending Count: {}, Running Count: {}, Rollout State: {}".format(
                        service_name,
                        deployment["pendingCount"],
                        deployment["runningCount"],
                        deployment["rolloutState"],
                    )
                )
                if deployment["rolloutState"] == "COMPLETED":
                    print("Rollout completed")
                    rollout_finalized = True
                    break
                elif deployment["rolloutState"] == "FAILED":
                    print("Rollout failed")
                    rollout_finalized = True
                    break
                if deployment["failedTasks"] > 0:
                    print("Rollout failed. Number of failed tasks is greater than 0")
                    rollout_finalized = True
                    break
    if rollout_finalized:
        break
    time.sleep(5)
