#!/bin/bash
set -ex
echo
if [ -z "$AWS_ACCESS_KEY_ID" ]
then
  echo "Setting AWS_PROFILE=prod/prod_admin"
  export AWS_PROFILE=prod/prod_admin
fi

# Define the environment file path
env_file=".env"

# Check if the environment file exists
if [ -f "$env_file" ]; then
  # Source the environment file if it exists
  source "$env_file"
else
  # If the environment file does not exist, print an error message
  echo "Environment file $env_file does not exist. Not sourcing .env"
fi

echo
echo "Updating aws-cli"
echo
pip install --upgrade awscli

echo
echo "Logging in to AWS ECR for 940552945933.dkr.ecr.us-west-2.amazonaws.com"
echo
bash -c "aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 940552945933.dkr.ecr.us-west-2.amazonaws.com"

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

if [ "prod" == "prod" ]; then
  if [ "$BRANCH" != "main" ]; then
    echo "Not on main branch, not deploying to prod"
    exit 1
  fi
fi

export VERSION_PATH="$VERSION-$GIT_HASH$GIT_DIRTY/$BRANCH/"
export UPLOAD_DIRECTORY="s3://noq-global-frontend/$VERSION_PATH"
export UPLOAD_DIRECTORY_V2="s3://noq-global-frontend/v2/$VERSION_PATH"
export PUBLIC_URL="https://d2mxcvfujf7a5q.cloudfront.net/$VERSION_PATH"
export PUBLIC_URL_V2="https://d2mxcvfujf7a5q.cloudfront.net/v2/$VERSION_PATH"
export DOCKER_IMAGE_NAME=shared-prod-registry-api
export DOCKER_IMAGE_TAG_LATEST=shared-prod-registry-api:latest
export DOCKER_IMAGE_TAG_VERSIONED=shared-prod-registry-api:$VERSION
export ECR_IMAGE_TAG_LATEST=940552945933.dkr.ecr.us-west-2.amazonaws.com:latest

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
    --build-arg IAMBIC_REPO_USER="$IAMBIC_REPO_USER" \
    --build-arg IAMBIC_REPO_TOKEN="$IAMBIC_REPO_TOKEN" \
    --build-arg PUBLIC_URL="$PUBLIC_URL" \
    --build-arg PUBLIC_URL_V2="$PUBLIC_URL_V2" \
    -t $DOCKER_IMAGE_NAME \
    --progress=plain \
    .

docker tag $DOCKER_IMAGE_TAG_LATEST \
  940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:latest

docker tag $DOCKER_IMAGE_TAG_LATEST \
  940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:$VERSION

echo
echo "Pushing API container - $VERSION"
echo
docker push --all-tags 940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api

echo
echo "Copying Frontend from container to S3"
echo

# Upload frontend files that we just built in the container to S3
if [ -z "$AWS_ACCESS_KEY_ID" ]
then
  # Get production creds
  export PROD_ROLE_ARN=arn:aws:iam::940552945933:role/prod_admin
  noq file -p $PROD_ROLE_ARN $PROD_ROLE_ARN -f
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:latest \
    bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:latest \
    bash -c "aws s3 sync /app/ui/dist/ $UPLOAD_DIRECTORY_V2"
else
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:latest bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    940552945933.dkr.ecr.us-west-2.amazonaws.com/shared-prod-registry-api:latest bash -c "aws s3 sync /app/ui/dist/ $UPLOAD_DIRECTORY_V2"
fi

echo
echo "Deploying Service - $VERSION"
echo
python deploy/infrastructure/live/shared/prod-1/ecs_deployer.py