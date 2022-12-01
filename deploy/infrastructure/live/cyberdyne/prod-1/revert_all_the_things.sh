#!/bin/bash
set -ex
echo
echo "Checking whether VIRTUALENV exists in your environment"
echo
if [[ -z "${VIRTUAL_ENV}" && -z "${VIRTUALENVWRAPPER_PYTHON}" && -z "${PYENV_ROOT}" ]]; then
    echo "Definitely need to have either VIRTUAL_ENV, VIRTUALENVWRAPPER_PYTHON or PYENV_ROOT defined, which means"
    echo "you have to choose either venv, virtualenvwrapper or pyenv to install all requirements while we"
    echo "work on making bazel hermetic"
    exit 1
fi

echo
echo "Setting AWS_PROFILE=cyberdyne_demo_org/cyberdyne_admin"
echo
export AWS_PROFILE=cyberdyne_demo_org/cyberdyne_admin

echo
echo "Updating aws-cli"
echo
pip install --upgrade awscli

echo
echo "Logging in to AWS ECR for 775726381634.dkr.ecr.us-west-2.amazonaws.com"
echo
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 775726381634.dkr.ecr.us-west-2.amazonaws.com

echo
echo "Reverting Service"
echo
bazelisk run //deploy/infrastructure/live/cyberdyne/prod-1:ecs_undeployer