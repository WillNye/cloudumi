filegroup(
    name = "prod-1-files",
    srcs = glob([
        "*.yaml",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "prod-1",
    srcs = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
        ":prod-1-files",
    ],
    executable = True,
    exec_tools = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
    ],
    outs = ["run_deploy_prod"],
    message = "Deploying CloudUmi to prod...",
    cmd = "echo 'bazel run //api:container-deploy-prod; \
           \
           bazel run //common/celery_tasks:container-deploy-prod; \
           \
           ecs-cli configure --cluster noq-dev-shared-prod-1 --default-launch-type FARGATE \
           --config-name noq-dev-shared-prod-1 --region us-west-2; \
           \
           ecs-cli up --cluster-config noq-dev-shared-prod-1; \
           \
           ecs-cli compose -f deploy/infrastructure/live/shared/prod-1/compose.yaml \
           --cluster-config noq-dev-shared-prod-1 \
           --ecs-params deploy/infrastructure/live/shared/prod-1/ecs.yaml \
           -p noq-dev-shared-prod-1 \
           --task-role-arn arn:aws:iam::940552945933:role/noq-dev-shared-prod-1-ecsTaskRole \
           --region us-west-2 service up --create-log-groups --timeout 15 \
           --target-groups targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:940552945933:targetgroup/tf-20220204014458666900000002/e4170783a27e99b0,containerName=noq-dev-shared-prod-1-api,containerPort=8092' >$@",
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
    cmd = "ecs-cli compose -f deploy/infrastructure/live/shared/prod-1/compose.yaml \
           -p noq-dev-shared-prod-1 service rm \
           \
           ecs-cli down --cluster-config noq-dev-shared-prod-1; >$@",
    tags = ["manual"],
)