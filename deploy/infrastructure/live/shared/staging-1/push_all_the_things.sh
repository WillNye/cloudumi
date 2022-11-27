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

echo
echo "Building and tagging docker image"
echo

docker build --platform=linux/amd64 \
    --build-arg PUBLIC_URL="$PUBLIC_URL" \
    -t shared-staging-registry-api \
    --progress=plain \
    .

docker tag shared-staging-registry-api:latest \
  259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest

docker tag shared-staging-registry-api:latest \
  259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:$VERSION

echo
echo "Pushing API container - $VERSION"
echo
docker push --all-tags 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api

echo
echo "Copying Frontend from container to S3"
echo
export PROD_ROLE_ARN=arn:aws:iam::940552945933:role/prod_admin
noq file -p $PROD_ROLE_ARN $PROD_ROLE_ARN -f
docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"

echo
echo "Deploying Service - $VERSION"
echo
python deploy/infrastructure/live/shared/staging-1/ecs_deployer.py