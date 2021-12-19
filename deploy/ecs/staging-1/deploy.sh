# Deploy Web
# Staging env specific:
# Default VPC
# ecs-cli up --cluster-config noq-staging-1 --vpc vpc-08c119545d2e61713 --subnets subnet-0661531a5841a1af7,subnet-03326ba1edea63961 --force
ecs-cli configure --cluster noq-staging-1 --default-launch-type FARGATE --config-name noq-staging-1-web --region us-west-2
ecs-cli compose -f deploy/ecs/staging-1/docker-compose-ecs.yaml \
--cluster-config noq-staging-1-web --ecs-params deploy/ecs/staging-1/ecs-params.yml -p noq-staging --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
--region us-west-2 service up --create-log-groups --timeout 15 --target-groups "targetGroupArn=arn:aws:elasticloadbalancing:us-west-2:259868150464:targetgroup/noq-staging-1-tg/ff8c2ec3d5a449f5,containerPort=8092,containerName=noq-staging"

ecs-cli configure --cluster noq-staging-1 --default-launch-type FARGATE --config-name noq-staging-1-celery --region us-west-2

ecs-cli compose -f deploy/ecs/staging-1/docker-compose-ecs-celery.yaml \
--cluster-config noq-staging-1 --ecs-params deploy/ecs/staging-1/ecs-params.yml -p noq-staging-1-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
--region us-west-2 service up --create-log-groups --timeout 15

#ecs-cli configure --cluster noq-staging --default-launch-type FARGATE --config-name noq-staging-celery --region us-west-2
## Deploy Celery
#ecs-cli compose -f docker-compose-ecs-celery.yaml \
#--cluster-config noq-staging-celery --ecs-params ecs-params.yml -p noq-staging-celery --task-role-arn arn:aws:iam::259868150464:role/NoqClusterRole1 \
#--region us-west-2 service up --create-log-groups --timeout 15