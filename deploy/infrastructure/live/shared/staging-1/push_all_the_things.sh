#!/bin/bash
set -ex
echo
if [ -z "$AWS_ACCESS_KEY_ID" ]
then
  echo "Setting AWS_PROFILE=staging/staging_admin"
  export AWS_PROFILE=staging/staging_admin
fi

echo
echo "Updating aws-cli"
echo
pip install --upgrade awscli

echo
echo "Logging in to AWS ECR for 259868150464.dkr.ecr.us-west-2.amazonaws.com"
echo
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com

export VERSION=$(git describe --tags --abbrev=0)
export BRANCH=$(git symbolic-ref --short HEAD)
export GIT_HASH=$(git rev-parse --short HEAD)
export GIT_DIRTY="$(git diff --quiet || echo '-dirty')"
export UNTRACKED_FILES="$(git status -s)"

# Ask user to proceed if untracked files are present
if [ -n "$UNTRACKED_FILES" ]; then
    echo "Untracked files: $UNTRACKED_FILES\n"
    echo "Untracked files are present. Proceed? [y/n]"
    read -r proceed
    if [ "$proceed" != "y" ]; then
        echo "Exiting"
        exit 1
    fi
fi

if [ "staging" == "prod" ]; then
  if [ "$BRANCH" != "main" ]; then
    echo "Not on main branch, not deploying to prod"
    exit 0
  fi
fi

export VERSION_PATH="$VERSION-$GIT_HASH$GIT_DIRTY/$BRANCH/"
export UPLOAD_DIRECTORY="s3://noq-global-frontend/$VERSION_PATH"
export PUBLIC_URL="https://d2mxcvfujf7a5q.cloudfront.net/$VERSION_PATH"
export DOCKER_IMAGE_NAME=shared-staging-registry-api
export DOCKER_IMAGE_TAG_LATEST=shared-staging-registry-api:latest
export DOCKER_IMAGE_TAG_VERSIONED=shared-staging-registry-api:$VERSION
export ECR_IMAGE_TAG_LATEST=259868150464.dkr.ecr.us-west-2.amazonaws.com:latest

echo
echo "Removing older docker images"
echo

# TODO: How do we capture the older versions?
docker rmi --force $(docker images "$DOCKER_IMAGE_TAG_LATEST" -a -q) || true
docker rmi --force $(docker images "$DOCKER_IMAGE_TAG_VERSIONED" -a -q) || true
docker rmi --force $(docker images "$DOCKER_IMAGE_NAME" -a -q) || true

echo
echo "Building and tagging docker image"
echo

docker build --platform=linux/amd64 \
    --build-arg PUBLIC_URL="$PUBLIC_URL" \
    -t $DOCKER_IMAGE_NAME \
    --progress=plain \
    .

docker tag $DOCKER_IMAGE_TAG_LATEST \
  $ECR_IMAGE_TAG_LATEST

docker tag $DOCKER_IMAGE_TAG_LATEST \
  259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:$VERSION

echo
echo "Pushing API container - $VERSION"
echo
docker push --all-tags 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api

echo
echo "Copying Frontend from container to S3"
echo

# Get production creds
export PROD_ROLE_ARN=arn:aws:iam::940552945933:role/prod_admin
noq file -p $PROD_ROLE_ARN $PROD_ROLE_ARN -f

# Upload frontend files that we just built in the container to S3
docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" $ECR_IMAGE_TAG_LATEST \
    bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"

echo
echo "Deploying Service - $VERSION"
echo
python deploy/infrastructure/live/shared/staging-1/ecs_deployer.py