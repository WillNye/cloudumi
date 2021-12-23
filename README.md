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

## Pre-requisites
* Install ecs-cli: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_installation.html
* Install docker: https://docs.docker.com/get-docker/
* Install docker-compose: https://docs.docker.com/compose/install/
* Install bazelisk: https://github.com/bazelbuild/bazelisk/releases
* Optionally install pyenv: https://github.com/pyenv/pyenv#basic-github-checkout 

## Quick Start
* Ensure you have a python environment with version 3.9+
* Type: `bazelisk query //...` to get a list of all targets
* To build: `bazelisk build //...` - this builds everything locally
* To run the API container: `bazelisk run //api/local-container-dev` - this will install the container build in your local docker cache; you can run it with volumes mounted using the `docker run` command. The container name will be something like: `api:local-container-dev`.

## Setup your dev environment
### Containers
* Start your local dev environment by running: `bazelisk build //deploy/local:containers-dev` - this starts all the containers to run Cloudumi
* TODO: start all containers and py-binaries for projects

### Local environment
* Visual Studio Code (and pretty much any other IDE): we ship .vscode config files for VSC specifically to run targets. For other IDEs, ensure that your PYTHONPATH is set to the root of the mono repo; this "should" just work.
* For command line development: set your PYTHONPATH to the root of the monorepo - `PYTHONPATH=~/dev/noq/cloudumi python ...`
* For convenience we also include `py_venv` targets - you can run them thusly `bazelisk run //:lib-venv <target venv dir>` (for instance, use `bazelisk query //:all` to find all the `-venv` targets)
  * The venv targets will require an output venv that points to the path of the desired venv to store all internal and external deps in
  * You can use virtualenvwrapper as well by pointing the output argument at the root of the relevant venv under .virtualenvs: `bazelisk run //:lib-venv ~/.virtualenvs/noq` (for instance)

## More Bazel stuff

> Note on deployments - you must first authenticate with the ECR: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`.

> Also: you don't have to run all steps in sequence as the build targets depend on each other. For instance if you run the `//api:container-deploy-staging` target, it will automatically resolve the dependency chain, build the image, which depends on the library, which is built first.

### API
* Run a local test of the API service using one of the py_binary targets.
  * To run local-dev: `bazelisk run //api:bin.local`
  * To run S3-dev: `bazelisk run //api:bin.s3` -- note that the only difference here is that the config files are pulled form S3
* Build the API project library: `bazelisk build //api:lib`
* Test the API project library: `bazelisk test //api` -- coming SOON
* Run the API project local dev container: `bazelisk run //api:container-dev-local`
* Deploy the API project container to staging: `bazelisk run //api:container-deploy-staging`
* Deploy the API project container to production: `bazelisk run //api:container-deploy-prod`

### Build Celery
TODO

### Publish to Staging
Publishing to staging is a build target that utilizes a genrule syntax to deploy containers via the `ECS-CLI` tool. Make sure that you have the tool installed - see `Installing ECS-CLI`.

* `bazelisk build //deploy/staging:deploy`

### Publish to Prod
> Do you really want this? Do you have access?
TODO

## Troubleshooting
* In the event that docker containers fail to run with an error on a symbol not found *.so exception, use the `how to run in sysbox` instructions to run a fully isolated Ubuntu-based build environment that allows docker in docker on 20.04.

## How to run in sysbox
* Sysbox containers are fully fledged init containers with systemd and docker pre-installed
* Use the ubunty_sysbox Dockerfile to set up your environment to mirror your user name, directory, etc, then mount into the countainer your cloudumi repo and bazel cache                                                                 
* Customize:
* 1. Change ubunty_sysbox/Dockerfile and change all occurrences of "matt" to your user name
* 2. Build: `docker build -t local/ubuntu-focal-systemd-docker:latest`
* Then run the container: `docker run -v /home/matt/.aws:/home/matt/.aws -v /home/matt/.cache/bazel:/home/matt/.cache/bazel -v $(pwd):/cloudumi --runtime=sysbox-runc -it --rm -P --hostname=syscont local/ubuntu-focal-systemd-docker:latest`
* OR! run the container using the `docker-compose` orchestration script, from the project root: `docker-compose -f dev_environment/docker-compose-ubunty-sysbox.yml up -d`
  * And attach: `docker attach dev_environment_ubunty-sysbox_1`
* Once in the container, install python: `pyenv install 3.9.7`
