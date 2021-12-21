# Terraform instructions

## Initialize Terraform with backend

AWS_PROFILE=noq_dev terraform init

## Plan the changes

AWS_PROFILE=noq_dev terraform plan -var-file="staging.tfvars"

## Apply the changes

AWS_PROFILE=noq_dev terraform apply -var-file="staging.tfvars"

# Upload docker image to ECR manually

## Login to ECR

AWS_PROFILE=noq_dev aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com
docker build -t cloudumi .
docker tag cloudumi:latest 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest
docker push 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest

# ECS Staging instructions

AWS_PROFILE=noq_dev ecs-cli up --cluster-config noq-staging

# Build Instructions
Cloudumi is a mono repo and uses Bazel to build all of the distinct services. To get started, follow the Quick Start instructions below.

If you are unfamiliar with the bazel target syntax, take a moment to review the following: https://docs.bazel.build/versions/4.2.2/guide.html#specifying-targets-to-build.

Each target has a name that uniquely identifies a build target. The path disambiguates build targets within different projects / folders.

## Quick Start
* Get bazelisk from https://github.com/bazelbuild/bazelisk/releases
* Ensure you have a python environment with version 3.8.12 (required for building xmlsec) - I suggest installing pyenv to make python versioning easier: https://github.com/pyenv/pyenv#basic-github-checkout.
* Type: `bazelisk query //...` to get a list of all targets
* To build: `bazelisk build //...` - this builds everything locally
* To run the API container: `bazelisk run //api/local-container-dev` - this will install the container build in your local docker cache; you can run it with volumes mounted using the `docker run` command. The container name will be something like: `api:local-container-dev`.

## Troubleshooting
* In the event that docker containers fail to run with an error on a symbol not found *.so exception, use the `how to run in sysbox` instructions to run a fully isolated Ubuntu-based build environment that allows docker in docker on 20.04.

## How to run in sysbox
* Sysbox containers are fully fledged init containers with systemd and docker pre-installed
* Use the ubunty_sysbox Dockerfile to set up your environment to mirror your user name, directory, etc, then mount into the countainer your cloudumi repo and bazel cache                                                                 
* Customize:
* 1. Change ubunty_sysbox/Dockerfile and change all occurrences of "matt" to your user name
* 2. Build: `docker build -t local/ubuntu-focal-systemd-docker:latest`
* Then run the container: `docker run -v /home/matt/.cache/bazel:/home/matt/.cache/bazel -v $(pwd):/cloudumi --runtime=sysbox-runc -it --rm -P --hostname=syscont local/ubuntu-focal-systemd-docker:latest`
