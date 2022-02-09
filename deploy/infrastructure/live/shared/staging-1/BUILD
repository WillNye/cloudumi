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
    cmd = "echo 'echo \"NOTE: This script makes certain assumptions: most have noq_dev as a section in your ~/.aws/credentials (see READMEs), must have awscli installed pip install awscli\"; \
           \
           export AWS_PROFILE=noq_dev; \
           \
           aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com; \
           \
           ecs-cli configure --cluster staging-noq-dev-shared-staging-1 --default-launch-type FARGATE \
           --config-name staging-noq-dev-shared-staging-1 --region us-west-2; \
           \
           ecs-cli up --cluster-config staging-noq-dev-shared-staging-1; \
           \
           ecs-cli compose -f deploy/infrastructure/live/shared/staging-1/compose.yaml \
           --cluster-config staging-noq-dev-shared-staging-1 \
           --ecs-params deploy/infrastructure/live/shared/staging-1/ecs.yaml \
           -p staging-noq-dev-shared-staging-1 \
           --task-role-arn arn:aws:iam::259868150464:role/staging-noq-dev-shared-staging-1-ecsTaskRole \
           --region us-west-2 service up --create-log-groups --timeout 15 \
           --target-groups targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/tf-20220128193723710200000002/e84c2219c5ca74a8,containerName=staging-noq-dev-shared-staging-1-api,containerPort=8092' >$@",
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