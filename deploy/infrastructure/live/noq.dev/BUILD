filegroup(
    name = "noq.dev",
    data = glob([
        "*.tfvars",
        "*.yaml",
        "*.yml",
    ]),
    visibility = ["//visibility:public"],
)

genrule(
    name = "tf-staging",
    srcs = [
        "noq.dev",
    ],
    outs = ["terraform_apply_staging"],
    cmd  = "echo 'terraform apply --var-file=noq.dev-staging.tfvars' &>$@",
    executable = True,
    message = "This applies terraform staging configuration",
    tags = ["manual"],
)

genrule(
    name = "tf-production",
    srcs = [
        "noq.dev",
    ],
    outs = ["terraform_apply_prod"],
    cmd  = "echo 'terraform apply --var-file=noq.dev-prod.tfvars' &>$@",
    executable = True,
    message = "This applies terraform production configuration",
    tags = ["manual"],
)

# TODO: create a cloudumi deploy bazel rule taht does this cleanly.
genrule(
    name = "staging",
    srcs = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
        ":tf-staging",
    ],
    executable = True,
    exec_tools = [
        "//api:container-deploy-staging",
        "//common/celery_tasks:container-deploy-staging",
        "tf-staging",
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
           ecs-cli compose -f docker-compose-ecs-staging-api.yaml \
           --cluster-config noq-staging-1-api --ecs-params ecs-params-staging.yml \
           -p noq-staging-1-api --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
           targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-staging-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-staging; \
           \
           ecs-cli compose -f docker-compose-ecs-staging-celery.yaml \
           --cluster-config noq-staging-1-celery --ecs-params ecs-params-staging.yml \
           -p noq-staging-1-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)

# TODO: create a cloudumi deploy bazel rule that does this cleanly.
genrule(
    name = "production",
    srcs = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
        ":tf-production",
    ],
    exec_tools = [
        "//api:container-deploy-prod",
        "//common/celery_tasks:container-deploy-prod",
        ":tf-production",
    ],
    executable = True,
    outs = ["run_deploy"],
    message = "Deploying CloudUmi to production...",
    cmd = "echo 'bazel run //api:container-deploy-prod; \
                 bazel run //common/celery_tasks:container-deploy-prod; \
                 \
                 ecs-cli configure --cluster noq-production-1 --default-launch-type FARGATE \
                 --config-name noq-production-1-api --region us-west-2; \
                 \
                 ecs-cli configure --cluster noq-production-1 --default-launch-type FARGATE \
                 --config-name noq-production-1-celery --region us-west-2; \
                 \
                 ecs-cli compose -f docker-compose-ecs-production-api.yaml \
                 --cluster-config noq-production-1-api --ecs-params ecs-params-production.yml \
                 -p noq-production-1 --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
                 --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
                 targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-production-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-production; \
                 \
                 ecs-cli compose -f docker-compose-ecs-production-celery.yaml \
                 --cluster-config noq-production-1-celery --ecs-params ecs-params-production.yml \
                 -p noq-production-1 --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
                 --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)