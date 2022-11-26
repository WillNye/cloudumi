#!/bin/bash
set -ex
echo
echo "Setting AWS_PROFILE=staging/staging_admin"
echo
export AWS_PROFILE=staging/staging_admin

echo
echo "Updating aws-cli"
echo
pip install --upgrade awscli

echo
echo "Logging in to AWS ECR for 259868150464.dkr.ecr.us-west-2.amazonaws.com"
echo
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com

export VERSION=$(git describe --tags --abbrev=0)

echo
echo "Building and tagging docker image"
echo
docker build \
    -t shared-staging-registry-api \
    -t shared-staging-registry-celery \
    -t 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    -t 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:$VERSION \
    .

echo
echo "Pushing API container - $VERSION"
echo
# TODO: These are the same image, we should just reference the same container
docker push --all-tags 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api

echo
echo "Pushing Celery container - $VERSION"
echo
bazelisk run --action_env=AWS_PROFILE="$AWS_PROFILE" --stamp --workspace_status_command="echo VERSION $VERSION" //deploy/infrastructure/live/shared/staging-1:celery-container-deploy-staging

echo
echo "Deploying Service - $VERSION"
echo
VERSION=$VERSION bazelisk run //deploy/infrastructure/live/shared/staging-1:ecs_deployer