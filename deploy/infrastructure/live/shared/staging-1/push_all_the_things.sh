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

if [ "staging" == "prod" ]; then
  if [ "$BRANCH" != "main" ]; then
    echo "Not on main branch, not deploying to prod"
    exit 0
  fi
fi

export UPLOAD_DIRECTORY="s3://noq-global-frontend/$VERSION/$BRANCH/"
export PUBLIC_URL="https://d2mxcvfujf7a5q.cloudfront.net/$VERSION/$BRANCH/"

echo
echo "Building and tagging docker image"
echo

docker buildx build --platform=linux/amd64 \
    -t shared-staging-registry-api \
    -t shared-staging-registry-celery \
    -t 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    -t 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:$VERSION \
    --build-arg PUBLIC_URL="$PUBLIC_URL" \
    .

echo
echo "Copying Frontend from container to S3"
echo
export PROD_ROLE_ARN=arn:aws:iam::940552945933:role/prod_admin
noq file -p $PROD_ROLE_ARN $PROD_ROLE_ARN -f
docker run -v "$HOME/.aws:/root/.aws" \
    -e "AWS_PROFILE=$PROD_ROLE_ARN" 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api:latest \
    bash -c "aws s3 sync /app/frontend/dist/ $UPLOAD_DIRECTORY"

echo
echo "Pushing API container - $VERSION"
echo
noq file -p arn:aws:iam::940552945933:role/prod_admin arn:aws:iam::940552945933:role/prod_admin -f
docker push --all-tags 259868150464.dkr.ecr.us-west-2.amazonaws.com/shared-staging-registry-api

echo
echo "Deploying Service - $VERSION"
echo
python deploy/infrastructure/live/shared/staging-1/ecs_deployer.py