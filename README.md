# Welcome to NOQ

> Quick Start

- DevOps
  - [Deploy with Terraform and Bazel](deploy/README.md)
  - [Build with Bazel](#build-instructions)
- API:
  - [Overview](api/README.md)
- Backend:
  - [Celery Tasks](common/celery_tasks/README.md)
- Frontend:
  - [Overview](frontend/README.md)
- Docs:
  - [Overview](docs/README.md)
- How to Build:
  - [Build Instructions](#build-instructions)
- Testing:
  - [Testing Instructions](util/tests/README.md)
- Debugging and Troubleshooting:
  - [Debug/Troubleshoot](docs/debug_troubleshooting/README.md)

# Build Instructions

Cloudumi is a mono repo and uses Bazel to build all of the distinct services. To get started, follow the Quick Start instructions below.

If you are unfamiliar with the bazel target syntax, take a moment to review the following: https://docs.bazel.build/versions/4.2.2/guide.html#specifying-targets-to-build.

Each target has a name that uniquely identifies a build target. The path disambiguates build targets within different projects / folders.

## Pre-requisites

- Install ecs-cli: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_installation.html
- Install docker: https://docs.docker.com/get-docker/
- Install docker-compose: https://docs.docker.com/compose/install/
- Install bazelisk: https://github.com/bazelbuild/bazelisk/releases
  - Windows: `choco install bazelisk`
  - Mac: `brew install bazelisk`
- Optionally install ibazel: https://github.com/bazelbuild/bazel-watcher/releases
- Optionally install pyenv: https://github.com/pyenv/pyenv#basic-github-checkout
- Install python 3.9.x & dependencies (requirements-test.lock)
- Install tfsec: https://github.com/aquasecurity/tfsec#installation

## Quick Start

- Ensure you have a python environment with version 3.9+
- Type: `bazelisk query //...` to get a list of all targets
- To build: `bazelisk build //...` - this builds everything locally
- To run the API container: `bazelisk run //api/container` - this will install the container build in your local docker cache and run it
- To run the API container within Docker, you can also use `docker run`: `docker run -p 8092:8092 --env CONFIG_LOCATION=/configs/development_account/saas_development.yaml --env AWS_PROFILE=noq_cluster_dev --volume ~/.aws:/root/.aws --volume ~/.weep:/root/.weep bazel/api:container`

# Setup your dev environment

- Note: you can use `ibazel` to replace all `bazel` or `bazelisk` commands to speed up development. See [iBazel Overview](#ibazel-overview) for an example.

## Containers

- Start your local dev environment by running: `bazelisk build //deploy/local:containers-dev` - this starts all the containers to run Cloudumi
- To run test containers for CloudUmi API, Celery tasks, frontend, etc, use the `--add-host=cloudumi-redis:172.17.0.1` with the `docker run` command to link your container to the running local services (substitute cloudumi-redis as needed)
- TODO: start all containers and py-binaries for projects

## Local environment

- Visual Studio Code (and pretty much any other IDE): we ship .vscode config files for VSC specifically to run targets. For other IDEs, ensure that your PYTHONPATH is set to the root of the mono repo; this "should" just work. For VSCODE, just make sure you have the bazel plugin (and relevant plugin for your choice of IDE: https://marketplace.visualstudio.com/items?itemName=BazelBuild.vscode-bazel)
- For command line development: set your PYTHONPATH to the root of the monorepo - `PYTHONPATH=~/dev/noq/cloudumi python ...`

## iBazel Overview

- Recommend to install it in ~/bin and point your path at it
- Replace any `bazel` or `bazelisk` command with `ibazel`
- For instance: `ibazel run //api:bin` will automatically rebuild and re-run anytime an update is detected

# More Bazel stuff

> Note on deployments - you must first authenticate with the ECR: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`.

> Also: you don't have to run all steps in sequence as the build targets depend on each other. For instance if you run the `//api:container-deploy-staging` target, it will automatically resolve the dependency chain, build the image, which depends on the library, which is built first.

# Launch local test env

A local dev environment sets up testing. Test can be setup by running either the `bin` targets or the `container-dev-local` targets in each component's build file.

To setup the test environment, make sure you have `docker-compose` accessible in your environment, then:

- `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`: to setup the requisite containers for local services
- `bazelisk run //common/scripts:initialize_dynamodb`: to initialize the dynamo tables
- `bazelisk run //common/scripts:initialize_redis`: to initialize the redis cache

* To setup an account in the local dynamo instance run the following command:
  `python -m deploy.local.populate_services` or `bazelisk run //deploy/local:populate_services`

- Make any adjustments as needed
- Once you decide which way to run the NOQ services, do either of the following

## Local environment run

- Make sure you've [setup your environment](https://perimy.atlassian.net/wiki/spaces/MAIN/pages/41648129/Development+Environment+Setup)
- Launch dependency services: `bazelisk run //deploy/local:deps-only`
- `bazelisk run //api:bin`: to run the API in the local environment
- `bazelisk run //common/celery_tasks:bin`: to run the Celery workers in the local environment
- Navigate to https://cloudumidev.com

## Profiling

To profile a function all you have to do is `pip install pyinstrument` and drop in this snippet.

```python
import pyinstrument

p = pyinstrument.Profiler()
p.start()
# function or code snippet to profile
p.stop()
p.print(show_all=True)
```

## Container environment run

- Launch all services: `bazelisk run //deploy/local:containers-dev`

## Finding raw config

Configs are stored in dynamo which you can access at `localhost:8001`
The table containing raw configs is `dev_cloudumi_tenant_static_configs`
Within the UI you can perform all CRUD operations on your configs

### OR:

- Just run the services:
- `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`
- `bazelisk run //api:container-dev-local`: to run the API in the container environment
- `bazelisk run //common/celery_tasks:container-dev-local`: to run the Celery workers in the container environment

## Testing

You can use the `bazel test` command to run unit tests. A few pre-requisites:

- Ensure you have the ~/.weep/weep.yaml file also in /etc/weep in order for Weep to find it's configuration in the Bazel sandbox
- Then pre-auth in the browser: `AWS_PROFILE=noq_dev aws sts get-caller-identity`
- Run unit test as usual, for instance:
  - `bazel test //...` to run all unit tests configured using the `py_test` bazel target (see example in common/lib/tests/BUILD)
  - `bazel test //common/config/...` to run all unit tests in the config module

# Tech Debt

- We need to isolate all unit tests to stay with their components (we started on common/config)

# Hermetic Weep

- We are also looking at running hermetic Weep by adding the configuration via a Bazel filegroup, this is currently WIP and may or may not work as expected

# Versioning

We use GitVersion to automatically version our mono repo by providing modifier nouns in the commit message header: +semver: major, +semver: minor, +semver: patch.

# Troubleshooting

- In the event that docker containers fail to run with an error on a symbol not found \*.so exception, use the `how to run in sysbox` instructions to run a fully isolated Ubuntu-based build environment that allows docker in docker on 20.04.

## Tracing on locahost

We support Zipkin tracing when debugging locally. To enable tracing, update `configs/development_account/saas_development.yaml`
and uncomment the `tracing` section:

```yaml
tracing:
  enabled: true
```

Then run Zipkin: `docker run -d -p 9411:9411 openzipkin/zipkin`

Start the API, browse to Noq, then view traces at http://localhost:9411/

## Troubleshooting in Container

We use a slightly modified version of `ecsgo` to connect to our containers. Run the following commands to install `ecsgo`:

```bash
gh repo clone noqdev/ecsgo
cd ecsgo/cmd
go build
sudo cp ./cmd /usr/local/bin/ecsgo
```

To connect to the containers:

```bash
AWS_PROFILE=noq_staging ecsgo
# For prod
AWS_PROFILE=noq_prod ecsgo
```

Select the appropriate cluster, service, and tasks to connect to the container of your choice.

It may be useful to retrieve the environment variables used by the process in a Docker container running in Fargate.
This is so you have your CONFIG_LOCATION, bazel PYTHONPATH, and aws ECS credential environment variables set
appropriately without too much of a hassle. Run the following command to source all environment variables from the
container's primary process (PID 1):

```bash
. <(xargs -0 bash -c 'printf "export %q\n" "$@"' -- < /proc/1/environ)
for m in $(find /app -maxdepth 1 -type d -iname "cloudumi*"); do export PYTHONPATH=$PYTHONPATH:$m; done;
```

### Connecting to Celery Flower

Celery Flower contains a web interface that details Celery task status.
To connect to the web interface, install [ecs-tunnel](https://github.com/alastairmccormack/ecs-tunnel) and run the following command (Replace the cluster and task IDs as appropriate)

```bash
AWS_PROFILE=noq_staging ecs-tunnel -L 7101:7101 -c staging-noq-dev-shared-staging-1 -t 21e241ef65b74408b3be12648e1a3e94 --region us-west-2
```

```bash
AWS_PROFILE=noq_prod ecs-tunnel -L 7101:7101 -c noq-dev-shared-prod-1 -t 6a26122f6fdb4aeda3fdb3b62124b70e --region us-west-2
```
