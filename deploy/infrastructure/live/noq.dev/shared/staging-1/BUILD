filegroup(
    name = "staging-1-files",
    srcs = glob([
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
           ecs-cli compose -f deploy/infrastructure/live/noq.dev/shared/staging-1/compose.yaml \
           --cluster-config noq-dev-shared-staging-1 \
           --ecs-params deploy/infrastructure/live/noq.dev/shared/staging-1/ecs.yaml \
           -p noq-dev-shared-staging-1 \
           --task-role-arn arn:aws:iam::259868150464:role/noq-dev-shared-staging-1-ecsTaskRole \
           --region us-west-2 service up --create-log-groups --timeout 15 \
           --target-groups targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/tf-20220125225929622300000002/d07b266a92b2f1c3,containerName=noq-dev-shared-staging-1-api,containerPort=8092' >$@",
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
    cmd = "ecs-cli down --force --cluster-config noq-dev-shared-staging-1; >$@",
    tags = ["manual"],
)