#!/bin/bash
set -ex
echo
if [ -z "$AWS_ACCESS_KEY_ID" ]
then
  echo "Setting AWS_PROFILE=staging/staging_admin"
  export AWS_PROFILE=staging/staging_admin
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
echo "Logging in to AWS ECR for 259868150464.dkr.ecr.us-west-2.amazonaws.com"
echo
bash -c "aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com"

export BRANCH=$(git symbolic-ref --short HEAD)

if [ "staging" == "prod" ]; then
  if [ "$BRANCH" != "main" ]; then
    echo "Not on main branch, not deploying to prod"
    exit 1
  fi
fi

export UNTRACKED_FILES="$(git ls-files --others --exclude-standard)"
# Stash untracked files if they exist
if [ -n "$UNTRACKED_FILES" ]; then
    echo "Stashing untracked files"
    git stash save --include-untracked >/dev/null
    STATUS=$?
    if [ $STATUS -ne 0 ]; then
      exit $STATUS
    fi
fi

# Catch exit signal to apply the stash
trap 'if [ -n "$UNTRACKED_FILES" ]; then
         echo "Applying stash to bring back untracked files";
         git stash apply >/dev/null
         STATUS=$?
         if [ $STATUS -ne 0 ]; then
            exit $STATUS
         fi
      fi' EXIT

export VERSION=$(git describe --tags --abbrev=0)
export GIT_HASH=$(git rev-parse --short HEAD)
export GIT_DIRTY="$(git diff --quiet || echo '-dirty')"

export VERSION_PATH="$VERSION-$GIT_HASH$GIT_DIRTY/$BRANCH/"
export UPLOAD_DIRECTORY="s3://noq-global-frontend/$VERSION_PATH"
export UPLOAD_DIRECTORY_V2="s3://noq-global-frontend/v2/$VERSION_PATH"
export PUBLIC_URL="https://d2mxcvfujf7a5q.cloudfront.net/$VERSION_PATH"
export PUBLIC_URL_V2="https://d2mxcvfujf7a5q.cloudfront.net/v2/$VERSION_PATH"
export DOCKER_IMAGE_NAME=shared-staging-registry-api
export DOCKER_IMAGE_TAG_LATEST=shared-staging-registry-api:latest
export DOCKER_IMAGE_TAG_VERSIONED=shared-staging-registry-api:$VERSION
export ECR_IMAGE_TAG_LATEST=259868150464.dkr.ecr.us-west-2.amazonaws.com:latest
export DISK_USAGE_THRESHOLD=80

# Get the current disk usage percentage
export DISK_USAGE_PERCENTAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//g')

if (( USAGE > THRESHOLD )); then
  echo "Disk space above $THRESHOLD%. Removing older docker images."
  docker rmi --force $(docker images "$DOCKER_IMAGE_TAG_LATEST" -a -q) || true
  docker rmi --force $(docker images "$DOCKER_IMAGE_TAG_VERSIONED" -a -q) || true
  docker rmi --force $(docker images "$DOCKER_IMAGE_NAME" -a -q) || true
else
  echo "Disk space is below threshold. Skipping docker image cleanup."
fi

echo
echo "Building and tagging docker image"
echo

docker build --platform=linux/amd64 \
    --build-arg PUBLIC_URL="$PUBLIC_URL" \
    --build-arg PUBLIC_URL_V2="$PUBLIC_URL_V2" \
    -t $DOCKER_IMAGE_NAME \
    --progress=plain \
    .

docker tag $DOCKER_IMAGE_TAG_LATEST \
  259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest

docker tag $DOCKER_IMAGE_TAG_LATEST \
  259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:$VERSION

echo
echo "Pushing API container - $VERSION"
echo
docker push --all-tags 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api

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
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    bash -c "aws s3 sync /app/ui/dist/ $UPLOAD_DIRECTORY_V2"
else
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"
  docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest bash -c "aws s3 sync /app/ui/dist/ $UPLOAD_DIRECTORY_V2"
fi

echo
echo "Deploying Service - $VERSION"
echo
python deploy/infrastructure/live/shared/staging-1/ecs_deployer.py