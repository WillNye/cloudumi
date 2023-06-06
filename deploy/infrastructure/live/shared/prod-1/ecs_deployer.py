import os
import pathlib
import sys
import time
from collections import defaultdict

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
                "containerName": "noq-dev-shared-prod-1-api",
                "containerPort": 8092,
                "targetGroupArn": "arn:aws:elasticloadbalancing:us-west-2:940552945933:targetgroup/tf-20220210004707474900000002/bff21530b0388c25",
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
        "desiredCount": 2,
    },
    {
        "service": "celery_flower",
        "task_definition": f"{current_path}/task_definition_celery_flower.yaml",
        "desiredCount": 1,
    },
]

preflight_task_definition_map = []

cluster_name = "noq-dev-shared-prod-1"
subnets = ["subnet-0335e107c814d63f5", "subnet-06b4ff38d90fa1b9b"]
security_groups = ["sg-0e7a1ca3c697feb53"]
region = "us-west-2"
account_id = "940552945933"
kms_key_arn = (
    "arn:aws:kms:us-west-2:940552945933:key/4705da2e-1c2a-4594-bf31-b240e1daa8ab"
)
noq_ecs_log_group_name = "noq-dev-shared-prod-1"
version = os.getenv("VERSION")

ecr_client = boto3.client("ecr", region_name=region)
response = ecr_client.get_authorization_token(
    registryIds=[
        account_id,
    ]
)

ecs_client = boto3.client("ecs", region_name=region)

identity_res = boto3.client("sts").get_caller_identity()
identity = identity_res["Arn"].replace(":sts:", ":iam:").replace("assumed-role", "role")


def get_task_failure_reason(cluster_name, task_arn):
    ecs_client = boto3.client("ecs", region_name=region)
    task_details = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
    task = task_details["tasks"][0]

    if task.get("stoppedReason"):
        return task["stoppedReason"]

    container_reasons = [
        container["reason"]
        for container in task["containers"]
        if container.get("reason")
    ]

    return ", ".join(container_reasons)


def get_task_log_stream(log_group_name, log_stream_name_prefix):
    logs_client = boto3.client("logs", region_name=region)

    response = logs_client.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name_prefix,
    )

    log_streams = response["logStreams"]

    if log_streams:
        # Sort log streams by the last event time
        log_streams = sorted(log_streams, key=lambda x: x["creationTime"], reverse=True)
        return log_streams[0]["logStreamName"]
    else:
        return None


def print_new_log_events(
    log_group_name, log_stream_name_prefix, start_time, container_name, task_name
):
    logs_client = boto3.client("logs", region_name=region)
    try:
        log_stream_name = get_task_log_stream(log_group_name, log_stream_name_prefix)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return None
        else:
            raise

    new_start_time = start_time
    if log_stream_name and isinstance(start_time, int):
        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            startTime=start_time,
            startFromHead=False,
        )

        for event in response["events"]:
            print(
                f"{task_name} - {container_name} - {event['timestamp']}: {event['message']}"
            )
            new_start_time = event["timestamp"] + 1

        return new_start_time
    else:
        return None


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

for task in preflight_task_definition_map:
    with open(task["task_definition"]) as fp:
        task_definition = yaml.load(fp, Loader=yaml.FullLoader)

        for container in task_definition.get("containerDefinitions", []):
            if version:
                print(
                    f"Updating image version to {version} from configured env var VERSION"
                )
                container["image"] = container["image"].split(":")[0] + f":{version}"

        registered_task_definition = ecs_client.register_task_definition(
            **task_definition
        )

        task_definition_name = "{}:{}".format(
            registered_task_definition["taskDefinition"]["family"],
            registered_task_definition["taskDefinition"]["revision"],
        )

        response = ecs_client.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition_name,
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

        task["arns"] = [task["taskArn"] for task in response["tasks"]]

service_rollout_completed = 0
rollout_finalized = False
failed = False
start_time = defaultdict(int)
next_token = None

while True:
    if rollout_finalized:
        break

    for task in preflight_task_definition_map:
        task_arn = task["arns"][0]
        task_details = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        task["status"] = task_details["tasks"][0]["lastStatus"]

        # Check all the containers in the task for the exit code, and not just the first one
        task_failures = sum(
            [
                container.get("exitCode", 0)
                for container in task_details["tasks"][0]["containers"]
                if container.get("exitCode", 0) != 0
            ]
        )

        if task_failures > 0:
            failure_reason = get_task_failure_reason(cluster_name, task_arn)
            print(f"Task: {task}, failed: {task_failures}")
            print(f"Failure reason: {failure_reason}")
            failed = True
            break

    service_rollout_completed = len(
        [
            task
            for task in preflight_task_definition_map
            if task["status"] == "STOPPED"
            or task["status"] == "DEPROVISIONING"
            or task["status"] == "STOPPING"
        ]
    )

    if len(preflight_task_definition_map) == service_rollout_completed:
        rollout_finalized = True

    if failed is True:
        print(
            "Rollout failed - tasks as defined in the preflight_task_definition_map have failed"
        )
        break

    print(
        f"Currently waiting for {len(preflight_task_definition_map)} preflight tasks to complete:\n{[[x.get('task'), x.get('status'), x.get('arns')] for x in preflight_task_definition_map if x['status'] != 'STOPPED']}"
    )

    for task in preflight_task_definition_map:
        task_name = task["task"]

        with open(task["task_definition"]) as fp:
            task_definition = yaml.load(fp, Loader=yaml.FullLoader)

        task_id = task["arns"][0].split("/")[-1]
        cluster_prefix = task_definition["containerDefinitions"][0]["logConfiguration"][
            "options"
        ]["awslogs-stream-prefix"]
        name = task_definition["containerDefinitions"][0]["name"]
        awslogs_stream_prefix = f"{cluster_prefix}/{name}/{task_id}"
        awslogs_group = task_definition["containerDefinitions"][0]["logConfiguration"][
            "options"
        ]["awslogs-group"]
        for container in task_definition.get("containerDefinitions", []):
            container_name = container["name"]
            awslogs_stream_prefix = f"{cluster_prefix}/{container_name}/{task_id}"
            result = print_new_log_events(
                awslogs_group,
                awslogs_stream_prefix,
                start_time.get(task_name, 0),
                container_name,
                task_name,
            )
            if result is None:
                print(
                    f"Task {task_name} and container {container_name} has not started logging yet"
                )
            else:
                start_time[task_name] = result

    time.sleep(5.0)

if failed is True:
    sys.exit(1)

for service in service_task_definition_map:
    service_name = service["service"]

    with open(service["task_definition"], "r") as f:
        task_definition = yaml.load(f, Loader=yaml.FullLoader)

        for task in task_definition.get("containerDefinitions", []):
            if version:
                print(
                    f"Updating image version to {version} from configured env var VERSION"
                )
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
failed = False

while True:
    if service_rollout_completed == len(service_task_definition_map):
        break

    if rollout_finalized:
        break

    if failed is True:
        break

    for service in service_task_definition_map:
        if service.get("status") in ["COMPLETED", "FAILED"]:
            continue
        service_name = service["service"]
        service_status = ecs_client.describe_services(
            cluster=cluster_name, services=[service_name]
        )
        if service.get("arn") is None:
            service["arn"] = service_status["services"][0]["serviceArn"]
        if service.get("taskArns") is []:
            service["taskArns"] = ecs_client.list_tasks(
                cluster=cluster_name, serviceName=service_name
            ).get("taskArns", [])
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
                        failed = True
                        break

    for service in service_task_definition_map:
        with open(service["task_definition"], "r") as f:
            task_definition = yaml.load(f, Loader=yaml.FullLoader)

        service_name = service["service"]
        cluster_prefix = task_definition["containerDefinitions"][0]["logConfiguration"][
            "options"
        ]["awslogs-stream-prefix"]
        name = task_definition["containerDefinitions"][0]["name"]
        for task_arn in service.get("taskArns", []):
            task_id = task_arn.split("/")[-1]
            awslogs_stream_prefix = f"{cluster_prefix}/{name}/{task_id}"
            awslogs_group = task_definition["containerDefinitions"][0][
                "logConfiguration"
            ]["options"]["awslogs-group"]

            for container in task_definition.get("containerDefinitions", []):
                container_name = container["name"]
                awslogs_stream_prefix = f"{cluster_prefix}/{container_name}/{task_id}"
                result = print_new_log_events(
                    awslogs_group,
                    awslogs_stream_prefix,
                    start_time.get(service_name, 0),
                    container_name,
                    service_name,
                )
                if result is None:
                    print(
                        f"Service {service_name} and container {container_name} has not started logging yet"
                    )
                else:
                    start_time[service_name] = result

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
        f"AWS_PROFILE={os.environ.get('AWS_PROFILE', identity)} ecs-cli logs --region {region} --task-id {task_id} -c {cluster_name} --follow\n"
    )

if failed:
    sys.exit(1)
