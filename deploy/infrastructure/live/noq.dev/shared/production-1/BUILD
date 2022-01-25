filegroup(
    name = "production-1-files",
    data = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "production-1",
    srcs = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
        ":production-1-files",
    ],
    exec_tools = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
    ],
    executable = True,
    outs = ["run_deploy_production"],
    message = "Deploying CloudUmi to production...",
    cmd = "echo 'bazel run //api:container-deploy-prod; \
                 bazel run //common/celery_tasks:container-deploy-prod; \
                 \
                 ecs-cli configure --cluster noq-common-production-1 --default-launch-type FARGATE \
                 --config-name noq-common-production-1-api --region us-west-2; \
                 \
                 ecs-cli configure --cluster noq-common-production-1 --default-launch-type FARGATE \
                 --config-name noq-common-production-1-celery --region us-west-2; \
                 \
                 ecs-cli up --cluster-config noq-common-production-1-api; \
                 \
                 ecs-cli up --cluster-config noq-common-production-1-celery; \
                 \
                 ecs-cli compose -f deploy/infrastructure/live/noq.dev/production-1/docker-compose-ecs-noq-common-production-1-api.yaml \
                 --cluster-config noq-common-production-1-api --ecs-params deploy/infrastructure/live/noq.dev/production-1/ecs-params-noq-common-production-1.yml \
                 -p noq-common-production-1 --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
                 --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
                 targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-common-production-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-production; \
                 \
                 ecs-cli compose -f deploy/infrastructure/live/noq.dev/production-1/docker-compose-ecs-noq-common-production-1-celery.yaml \
                 --cluster-config noq-common-production-1-celery --ecs-params deploy/infrastructure/live/noq.dev/production-1/ecs-params-noq-common-production-1.yml \
                 -p noq-common-production-1 --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
                 --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)