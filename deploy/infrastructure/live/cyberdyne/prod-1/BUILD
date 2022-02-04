load("@io_bazel_rules_docker//container:container.bzl", "container_push")

filegroup(
    name = "prod-1-files",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

container_push(
    name = "api-container-deploy-prod",
    format = "Docker",
    repository = "cyberdyne-prod-registry-api",
    image = "//api:container",
    registry = "940552945933.dkr.ecr.us-west-2.amazonaws.com",
    tag = "prod",
    visibility = ["//visibility:public"],
)

container_push(
    name = "celery-container-deploy-prod",
    format = "Docker",
    repository = "cyberdyne-prod-registry-celery",
    image = "//common/celery_tasks:container",
    registry = "940552945933.dkr.ecr.us-west-2.amazonaws.com",
    tag = "prod",
    visibility = ["//visibility:public"],
)

genrule(
    name = "prod-1",
    srcs = [
        ":api-container-deploy-prod",
        ":celery-container-deploy-prod",
        ":prod-1-files",
    ],
    executable = True,
    exec_tools = [
        ":api-container-deploy-prod",
        ":celery-container-deploy-prod",
    ],
    outs = ["run_deploy_prod"],
    message = "Deploying CloudUmi to prod...",
    cmd = "echo 'echo \"NOTE: This script makes certain assumptions: most have noq_prod as a section in your ~/.aws/credentials (see READMEs), must have awscli installed pip install awscli\"; \
           \
           export AWS_PROFILE=noq_prod; \
           \
           aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 940552945933.dkr.ecr.us-west-2.amazonaws.com; \
           \
           ecs-cli configure --cluster noq-dev-cyberdyne-prod-1 --default-launch-type FARGATE \
           --config-name noq-dev-cyberdyne-prod-1 --region us-west-2; \
           \
           ecs-cli up --cluster-config noq-dev-cyberdyne-prod-1; \
           \
           ecs-cli compose -f deploy/infrastructure/live/cyberdyne/prod-1/compose.yaml \
           --cluster-config noq-dev-cyberdyne-prod-1 \
           --ecs-params deploy/infrastructure/live/cyberdyne/prod-1/ecs.yaml \
           -p noq-dev-cyberdyne-prod-1 \
           --task-role-arn arn:aws:iam::940552945933:role/noq-dev-cyberdyne-prod-1-ecsTaskRole \
           --region us-west-2 service up --create-log-groups --timeout 15 \
           --target-groups targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:940552945933:targetgroup/tf-20220204195848333600000002/7a9134b845eae90e,containerName=noq-dev-cyberdyne-prod-1-api,containerPort=8092' >$@",
    tags = ["manual"],
)

genrule(
    name = "destroy",
    srcs = [
        ":prod-1-files",
    ],
    executable = True,
    outs = ["run_destroy_prod"],
    message = "Destroying CloudUmi in prod...",
    cmd = "ecs-cli compose -f deploy/infrastructure/live/cyberdyne/prod-1/compose.yaml \
           -p noq-dev-cyberdyne-prod-1 service rm \
           \
           ecs-cli down --cluster-config noq-dev-cyberdyne-prod-1; >$@",
    tags = ["manual"],
)