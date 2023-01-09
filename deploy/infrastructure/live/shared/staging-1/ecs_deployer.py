import os
import pathlib
import time

import boto3
import yaml
from botocore.exceptions import ClientError

current_path = pathlib.Path(__file__).parent.resolve()

service_task_definition_map = [
    {
        "service": "api",
        "task_definition": f"{current_path}/task_definition_api.yaml",
        "desiredCount": 1,
        "loadBalancers": [
            {
                "containerName": "staging-noq-dev-shared-staging-1-api",
                "containerPort": 8092,
                "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/tf-20220210002026526700000001/72dfc466694ddd66",
            },
        ],
    },
    {
        "service": "celery_scheduler",
        "task_definition": f"{current_path}/task_definition_celery_scheduler.yaml",
        "desiredCount": 1,
    },
    {
        "service": "celery_worker",
        "task_definition": f"{current_path}/task_definition_celery_worker.yaml",
        "desiredCount": 1,
    },
    {
        "service": "celery_flower",
        "task_definition": f"{current_path}/task_definition_celery_flower.yaml",
        "desiredCount": 1,
    },
]

cluster_name = "staging-noq-dev-shared-staging-1"
subnets = ["subnet-0dd8e008f770bd447", "subnet-0ae657185cbb32ee3"]
security_groups = ["sg-0344d82e7000960df"]
region = "us-west-2"
account_id = "259868150464"
kms_key_arn = (
    "arn:aws:kms:us-west-2:259868150464:key/c772a276-6f4d-455b-a2fc-99681435401e"
)
noq_ecs_log_group_name = "staging-noq-dev-shared-staging-1"
version = os.getenv("VERSION")

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

for service in service_task_definition_map:
    service_name = service["service"]

    with open(service["task_definition"], "r") as f:
        task_definition = yaml.load(f, Loader=yaml.FullLoader)

        for task in task_definition.get("containerDefinitions", []):
            task["image"] = task["image"].split(":")[0] + f":{version}"

        registered_task_definition = ecs_client.register_task_definition(
            **task_definition
        )

        task_definition_name = "{}:{}".format(
            registered_task_definition["taskDefinition"]["family"],
            registered_task_definition["taskDefinition"]["revision"],
        )

        try:
            service = ecs_client.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                taskDefinition=task_definition_name,
                desiredCount=service["desiredCount"],
                launchType="FARGATE",
                loadBalancers=service.get("loadBalancers", []),
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
                desiredCount=service["desiredCount"],
                loadBalancers=service.get("loadBalancers", []),
                enableExecuteCommand=True,
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnets,
                        "assignPublicIp": "DISABLED",
                        "securityGroups": security_groups,
                    }
                },
            )

service_rollout_completed = 0
rollout_finalized = False

while True:
    if service_rollout_completed == len(service_task_definition_map):
        break

    if rollout_finalized:
        break

    for service in service_task_definition_map:
        if service.get("status") in ["COMPLETED", "FAILED"]:
            continue
        service_name = service["service"]
        service_status = ecs_client.describe_services(
            cluster=cluster_name, services=[service_name]
        )
        for service_status in service_status["services"]:
            for deployment in service_status["deployments"]:
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
                        print(f"Service: {service_name}, Rollout completed")
                        service["status"] = "COMPLETED"
                        service_rollout_completed += 1
                        break
                    elif deployment["rolloutState"] == "FAILED":
                        print(f"Service: {service_name}, Rollout failed")
                        service["status"] = "FAILED"
                        service_rollout_completed += 1
                        break
                    if deployment["failedTasks"] > 0:
                        print(
                            f"Rollout failed. Number of failed tasks is greater than 0: {deployment}"
                        )
                        rollout_finalized = True
                        break
        time.sleep(5)


tasks = ecs_client.list_tasks(
    cluster=cluster_name,
    maxResults=100,
)

task_details = ecs_client.describe_tasks(
    cluster=cluster_name,
    tasks=tasks["taskArns"],
)

print("Commands to view task logs: ")
for task in task_details["tasks"]:
    task_id = task["taskArn"].split("/")[-1]
    print("ARN {} : ".format(task["taskDefinitionArn"]))
    print(
        f"AWS_PROFILE={os.environ['AWS_PROFILE']} ecs-cli logs --region {region} --task-id {task_id} -c {cluster_name} --follow\n"
    )
