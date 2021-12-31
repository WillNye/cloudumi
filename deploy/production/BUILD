genrule(
    name = "deploy",
    srcs = [
        "//api:container-deploy-production",
        "//common/celery_tasks:container-deploy-production",
        "//deploy/ecs/production-1:compose_files",
    ],
    executable = True,
    outs = ["run_deploy"],
    cmd = "echo 'ecs-cli configure --cluster noq-production-1 --default-launch-type FARGATE \
           --config-name noq-production-1-web --region us-west-2; \
           ecs-cli configure --cluster noq-production-1 --default-launch-type FARGATE \
           --config-name noq-production-1-celery --region us-west-2; ecs-cli compose -f deploy/ecs/production-1/docker-compose-ecs-api.yaml \
           --cluster-config noq-production-1-web --ecs-params deploy/ecs/production-1/ecs-params.yml \
           -p noq-production --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15 --target-groups \
           targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-production-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-production; \
           ecs-cli compose -f deploy/ecs/production-1/docker-compose-ecs-celery.yaml \
           --cluster-config noq-production-1-celery --ecs-params deploy/ecs/production-1/ecs-params.yml \
           -p noq-production-1-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
           --region us-west-2 service up --create-log-groups --timeout 15' >$@",
    tags = ["manual"],
)