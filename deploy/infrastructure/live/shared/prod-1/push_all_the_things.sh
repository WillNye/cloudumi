#!/bin/bash
echo
echo "Setting AWS_PROFILE=noq_prod"
echo
export AWS_PROFILE=noq_prod

echo
echo "Logging in to AWS ECR for 940552945933.dkr.ecr.us-west-2.amazonaws.com"
echo
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 940552945933.dkr.ecr.us-west-2.amazonaws.com

echo
echo "Pushing API container"
echo
bazelisk run //deploy/infrastructure/live/shared/prod-1:api-container-deploy-prod

echo
echo "Pushing Celery container"
echo
bazelisk run //deploy/infrastructure/live/shared/prod-1:celery-container-deploy-prod

echo
echo "Updating infrastructure"
echo
bazelisk run //deploy/infrastructure/live/shared/prod-1