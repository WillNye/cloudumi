# TODO: create a cloudumi deploy bazel rule taht does this cleanly.
genrule(
    name = "staging",
    srcs = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
        "//deploy/ecs/staging-1:compose_files",
    ],
    executable = True,
    exec_tools = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
        "//deploy/ecs/staging-1:compose_files",
    ],
    outs = ["run_deploy"],
    message = "Deploying CloudUmi to staging...",
    cmd = "echo 'bazel run //api:container-deploy-staging; \
           \
           bazel run //common/celery_tasks:container-deploy-staging; \
           \
           ecs-cli configure --cluster noq-staging-1 --default-launch-type FARGATE \
           --config-name noq-staging-1-api --region us-west-2; \
           \
           ecs-cli configure --cluster noq-staging-1 --default-launch-type FARGATE \
           --config-name noq-staging-1-celery --region us-west-2; \
           \
           ecs-cli up --cluster-config noq-staging-1-api; \
           \
           ecs-cli up --cluster-config noq-staging-1-celery; \
           \
           ecs-cli compose -f deploy/ecs/staging-1/docker-compose-ecs-api.yaml \
           --cluster-config noq-staging-1-api --ecs-params deploy/ecs/staging-1/ecs-params.yml \
           -p noq-staging-1-api --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
           targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-staging-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-staging; \
           \
           ecs-cli compose -f deploy/ecs/staging-1/docker-compose-ecs-celery.yaml \
           --cluster-config noq-staging-1-celery --ecs-params deploy/ecs/staging-1/ecs-params.yml \
           -p noq-staging-1-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)