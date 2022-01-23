filegroup(
    name = "staging-1-files",
    data = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "staging-1",
    srcs = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
        ":staging-1-files",
    ],
    executable = True,
    exec_tools = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
    ],
    outs = ["run_deploy_staging"],
    message = "Deploying CloudUmi to staging...",
    cmd = "echo 'bazel run //api:container-deploy-staging; \
           \
           bazel run //common/celery_tasks:container-deploy-staging; \
           \
           ecs-cli configure --cluster noq-common-staging-1 --default-launch-type FARGATE \
           --config-name noq-common-staging-1-api --region us-west-2; \
           \
           ecs-cli configure --cluster noq-common-staging-1 --default-launch-type FARGATE \
           --config-name noq-common-staging-1-celery --region us-west-2; \
           \
           ecs-cli up --cluster-config noq-common-staging-1-api; \
           \
           ecs-cli up --cluster-config noq-common-staging-1-celery; \
           \
           ecs-cli compose -f deploy/infrastructure/live/noq.dev/staging-1/docker-compose-ecs-noq-common-staging-1-api.yaml \
           --cluster-config noq-common-staging-1-api --ecs-params deploy/infrastructure/live/noq.dev/staging-1/ecs-params-noq-common-staging-1.yml \
           -p noq-common-staging-1-api --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
           targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-common-staging-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-staging; \
           \
           ecs-cli compose -f deploy/infrastructure/live/noq.dev/staging-1/docker-compose-ecs-noq-common-staging-1-celery.yaml \
           --cluster-config noq-common-staging-1-celery --ecs-params deploy/infrastructure/live/noq.dev/staging-1/ecs-params-noq-common-staging-1.yml \
           -p noq-common-staging-1-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)