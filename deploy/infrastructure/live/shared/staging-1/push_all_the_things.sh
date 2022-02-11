#!/bin/bash
echo
echo "Checking whether VIRTUALENV exists in your environment"
echo
if [[ -z "${VIRTUAL_ENV}" && -z "${VIRTUALENVWRAPPER_PYTHON}" && -z "${PYENV_ROOT}" ]]; then
    echo "Definitely need to have either VIRTUAL_ENV, VIRTUALENVWRAPPER_PYTHON or PYENV_ROOT defined, which means"
    echo "you have to choose either venv, virtualenvwrapper or pyenv to install all requirements while we"
    echo "work on making bazel hermetic"
    exit(1)
fi

echo
echo "Setting AWS_PROFILE=noq_dev"
echo
export AWS_PROFILE=noq_dev

echo
echo "Logging in to AWS ECR for 259868150464.dkr.ecr.us-west-2.amazonaws.com"
echo
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com

echo
echo "Pushing API container"
echo
bazelisk run //deploy/infrastructure/live/shared/staging-1:api-container-deploy-staging

echo
echo "Pushing Celery container"
echo
bazelisk run //deploy/infrastructure/live/shared/staging-1:celery-container-deploy-staging

echo
echo "Updating infrastructure"
echo
bazelisk run //deploy/infrastructure/live/shared/staging-1