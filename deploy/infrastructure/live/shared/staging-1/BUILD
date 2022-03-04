load("@io_bazel_rules_docker//container:container.bzl", "container_push")

filegroup(
    name = "staging-1-files",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

container_push(
    name = "api-container-deploy-staging",
    format = "Docker",
    repository = "shared-staging-registry-api",
    image = "//api:container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "staging",
    visibility = ["//visibility:public"],
)

container_push(
    name = "celery-container-deploy-staging",
    format = "Docker",
    repository = "shared-staging-registry-celery",
    image = "//common/celery_tasks:container",
    registry = "259868150464.dkr.ecr.us-west-2.amazonaws.com",
    tag = "staging",
    visibility = ["//visibility:public"],
)

genrule(
    name = "staging-1",
    srcs = [
        ":api-container-deploy-staging",
        ":celery-container-deploy-staging",
        ":staging-1-files",
    ],
    executable = True,
    exec_tools = [
        ":api-container-deploy-staging",
        ":celery-container-deploy-staging",
    ],
    outs = ["run_deploy_staging"],
    message = "Deploying CloudUmi to staging...",
    cmd = "echo 'echo \"NOTE: This script makes certain assumptions: most have noq_staging as a section in your ~/.aws/credentials (see READMEs), must have awscli installed pip install awscli\";' \
           \
           export AWS_PROFILE=noq_staging; \
           \
           aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com; \
           \
           aws ecs create-cluster --cluster-name staging-noq-dev-shared-staging-1; \
           \
           register_task_definition_output=`aws ecs register-task-definition --cli-input-yaml file://deploy/infrastructure/live/shared/staging-1/task_definition.yaml`; \
           \
           task_definition_name_version=`echo $$register_task_definition_output | jq \'.taskDefinition.taskDefinitionArn | split(\"/\")\'[1]`; \
           \
           aws ecs create-service --cluster staging-noq-dev-shared-staging-1 --service-name staging-noq-dev-shared-staging-1 \
            --task-definition $$task_definition_name_version --desired-count 1 --launch-type \"FARGATE\" --network-configuration \
            --enable-execute-command \
            \"awsvpcConfiguration={subnets=[subnet-0dd8e008f770bd447, subnet-0ae657185cbb32ee3],securityGroups=[sg-0344d82e7000960df]}\"; \
           \
           aws ecs update-service --cluster staging-noq-dev-shared-staging-1 --service staging-noq-dev-shared-staging-1 \
            --task-definition $$task_definition_name_version --desired-count 1 --enable-execute-command \
            --network-configuration \"awsvpcConfiguration={subnets=[subnet-0dd8e008f770bd447, subnet-0ae657185cbb32ee3],securityGroups=[sg-0344d82e7000960df]}\";' >$@",
    tags = ["manual"],
)

genrule(
    name = "destroy",
    srcs = [
        ":staging-1-files",
    ],
    executable = True,
    outs = ["run_destroy_staging"],
    message = "Destroying CloudUmi in staging...",
    cmd = "ecs-cli compose -f deploy/infrastructure/live/shared/staging-1/compose.yaml \
           -p staging-noq-dev-shared-staging-1 service rm \
           \
           ecs-cli down --cluster-config staging-noq-dev-shared-staging-1; >$@",
    tags = ["manual"],
)