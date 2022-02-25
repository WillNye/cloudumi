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
- How to Build:
  - [Build Instructions](#build-instructions)

# Build Instructions

Cloudumi is a mono repo and uses Bazel to build all of the distinct services. To get started, follow the Quick Start instructions below.

If you are unfamiliar with the bazel target syntax, take a moment to review the following: https://docs.bazel.build/versions/4.2.2/guide.html#specifying-targets-to-build.

Each target has a name that uniquely identifies a build target. The path disambiguates build targets within different projects / folders.

## Pre-requisites

- Install ecs-cli: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_installation.html
- Install docker: https://docs.docker.com/get-docker/
- Install docker-compose: https://docs.docker.com/compose/install/
- Install bazelisk: https://github.com/bazelbuild/bazelisk/releases
- Optionally install pyenv: https://github.com/pyenv/pyenv#basic-github-checkout
- Install python 3.8.x & dependencies (requirements-test.lock)
- Install tfsec: https://github.com/aquasecurity/tfsec#installation

## Quick Start

- Ensure you have a python environment with version 3.9+
- Type: `bazelisk query //...` to get a list of all targets
- To build: `bazelisk build //...` - this builds everything locally
- To run the API container: `bazelisk run //api/container` - this will install the container build in your local docker cache and run it

## Setup your dev environment

### Containers

- Start your local dev environment by running: `bazelisk build //deploy/local:containers-dev` - this starts all the containers to run Cloudumi
- To run test containers for CloudUmi API, Celery tasks, frontend, etc, use the `--add-host=cloudumi-redis:172.17.0.1` with the `docker run` command to link your container to the running local services (substitute cloudumi-redis as needed)
- TODO: start all containers and py-binaries for projects

### Local environment

- Visual Studio Code (and pretty much any other IDE): we ship .vscode config files for VSC specifically to run targets. For other IDEs, ensure that your PYTHONPATH is set to the root of the mono repo; this "should" just work. For VSCODE, just make sure you have the bazel plugin (and relevant plugin for your choice of IDE: https://marketplace.visualstudio.com/items?itemName=BazelBuild.vscode-bazel)
- For command line development: set your PYTHONPATH to the root of the monorepo - `PYTHONPATH=~/dev/noq/cloudumi python ...`

## More Bazel stuff

> Note on deployments - you must first authenticate with the ECR: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`.

> Also: you don't have to run all steps in sequence as the build targets depend on each other. For instance if you run the `//api:container-deploy-staging` target, it will automatically resolve the dependency chain, build the image, which depends on the library, which is built first.

### API

- Activate your local virtualenv first `. env/bin/activate` (Note: We haven't had success working with pyenv)
- Run a local test of the API service using one of the py_binary targets.
  - To run local-dev: `bazelisk run //api:bin`
  - To run S3-dev: `bazelisk run //api:bin.s3` -- note that the only difference here is that the config files are pulled from S3
- Build the API project library: `bazelisk build //api:lib`
- Test the API project library: `bazelisk test //api` -- coming SOON
- Run the API project local dev container: `bazelisk run //api:container-dev-local`
- Deploy the API project container to staging: `bazelisk run //api:container-deploy-staging`
- Deploy the API project container to production: `bazelisk run //api:container-deploy-prod`

### Build Celery

TODO

### Launch local test env

A local dev environment sets up testing. Test can be setup by running either the `bin` targets or the `container-dev-local` targets in each component's build file.

To setup the test environment, make sure you have `docker-compose` accessible in your environment, then:

- `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`: to setup the requisite containers for local services
- `bazelisk run //common/scripts:initialize_dynamodb`: to initialize the dynamo tables
- `bazelisk run //common/scripts:initialize_redis`: to initialize the redis cache

To enable the UX:

- `cd frontend`
- `yarn build_template`
- `cd ..`

* To setup an account in the local dynamo instance, browse to `localhost:8001` and find the table `dev_cloudumi_tenant_static_configs`. In the top right corner, there is a "Create Item" button, click it.
* In the entry screen, add this:

```json
{
  "host": "localhost",
  "updated_by": "curtis@noq.dev",
  "id": "master",
  "updated_at": "1642358978",
  "config": "_development_groups_override:\n- noq_admins@noq.dev\n_development_user_override: matt@noq.dev\naccount_ids_to_name:\n  '259868150464': '259868150464'\napplication_admin: noq_admins@noq.dev\nauth:\n  force_redirect_to_identity_provider: false\n  get_groups_from_google: false\n  get_user_by_oidc: false\ncache_resource_templates:\n  repositories:\n  - authentication_settings:\n      email: terraform@noq.dev\n    main_branch_name: master\n    name: consoleme\n    repo_url: https://github.com/Netflix/consoleme\n    resource_formats:\n    - terraform\n    resource_type_parser: null\n    terraform:\n      path_suffix: .tf\n    type: git\n    web_path: https://github.com/Netflix/consoleme\ncache_self_service_typeahead:\n  cache_resource_templates: true\nchallenge_url:\n  enabled: true\ncloud_credential_authorization_mapping:\n  role_tags:\n    authorized_groups_cli_only_tags:\n    - noq-authorized-cli-only\n    authorized_groups_tags:\n    - noq-authorized\n    - consoleme-authorized\ndevelopment: true\nenvironment: test\nget_user_by_oidc_settings:\n  access_token_audience: noq\n  access_token_response_key: access_token\n  client_scopes:\n  - email\n  - openid\n  grant_type: authorization_code\n  id_token_response_key: id_token\n  jwt_email_key: email\n  jwt_groups_key: groups\n  jwt_verify: true\n  metadata_url: https://accounts.google.com/.well-known/openid-configuration\n  resource: noq_tenant\ngoogle:\n  credential_subject:\n    noq.dev: curtis@noq.dev\nheaders:\n  identity:\n    enabled: false\n  role_login:\n    enabled: true\npolicies:\n  pre_role_arns_to_assume:\n  - external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43\n    role_arn: arn:aws:iam::259868150464:role/ConsoleMeCentralRole\n  role_name: ConsoleMeSpokeRole\nsecrets:\n  jwt_secret: 0oti94rDtoGaiTnU4cxhNsylIaVB6EOLC-CVNBFlwYo\nsite_config:\n  landing_url: /\ntenant_details:\n  creation_time: '2021-12-17T15:55:43.960096'\n  creator: curtis@noq.dev\n  external_id: 018e23e8-9b41-4d66-85f2-3d60cb2b3c43\nurl: http://localhost:8092\n"
}
```

- Make any adjustments as needed
- Once you decide which way to run the NOQ services, do either of the following

#### Local environment run

- Launch dependency services: `bazelisk run //deploy/local/deps-only`
- `bazelisk run //api:bin`: to run the API in the local environment
- `bazelisk run //common/celery_tasks:bin`: to run the Celery workers in the local environment

#### Container environment run

- Launch all services: `bazelisk run //deploy/local/containers-dev`

##### OR:

- Just run the services:
- `docker-compose -f deploy/docker-compose-dependencies.yaml up -d`
- `bazelisk run //api:container-dev-local`: to run the API in the container environment
- `bazelisk run //common/celery_tasks:container-dev-local`: to run the Celery workers in the container environment

### Publish to Staging

Publishing to staging is a build target that utilizes a genrule syntax to deploy containers via the `ECS-CLI` tool. Make sure that you have the tool installed - see `Installing ECS-CLI`.

- `bazelisk run //deploy/infrastructure/live/shared/staging-1:staging-1`

### Publish to Prod

> Do you really want this? Do you have access?

- `bazelisk run //deploy/infrastructure/live/shared/prod-1:prod-1`

## Testing

You can use the `bazel test` command to run unit tests. A few pre-requisites:

- Ensure you have the ~/.weep/weep.yaml file also in /etc/weep in order for Weep to find it's configuration in the Bazel sandbox
- Then pre-auth in the browser: `AWS_PROFILE=noq_dev aws sts get-caller-identity`
- Run unit test as usual, for instance:
  - `bazel test //...` to run all unit tests configured using the `py_test` bazel target (see example in common/lib/tests/BUILD)
  - `bazel test //common/config/...` to run all unit tests in the config module

### Tech Debt

- We need to isolate all unit tests to stay with their components (we started on common/config)

### Hermetic Weep

- We are also looking at running hermetic Weep by adding the configuration via a Bazel filegroup, this is currently WIP and may or may not work as expected

## Versioning

We use GitVersion to automatically version our mono repo by providing modifier nouns in the commit message header: semver:+minor, semver:+minor, semver:+patch.

## Troubleshooting

- In the event that docker containers fail to run with an error on a symbol not found \*.so exception, use the `how to run in sysbox` instructions to run a fully isolated Ubuntu-based build environment that allows docker in docker on 20.04.

### Troubleshooting in Container (SSH Rules)

- It may be useful to retrieve the environment variables used by the process in a Docker container running in Fargate.
  This is so you have your CONFIG_LOCATION, bazel PYTHONPATH, and aws ECS credential environment variables set
  appropriately without too much of a hassle. Run the following command to source all environment variables from the
  container's primary process (PID 1):
  - `. <(xargs -0 bash -c 'printf "export %q\n" "$@"' -- < /proc/1/environ)`

## How to run in sysbox

- Sysbox containers are fully fledged init containers with systemd and docker pre-installed
- Use the ubunty_sysbox Dockerfile to set up your environment to mirror your user name, directory, etc, then mount into the countainer your cloudumi repo and bazel cache
- Customize:
- 1. Change ubunty_sysbox/Dockerfile and change all occurrences of "matt" to your user name
- 2. Build: `docker build -t local/ubuntu-focal-systemd-docker:latest`
- Then run the container: `docker run -v /home/matt/.aws:/home/matt/.aws -v /home/matt/.cache/bazel:/home/matt/.cache/bazel -v $(pwd):/cloudumi --runtime=sysbox-runc -it --rm -P --hostname=syscont local/ubuntu-focal-systemd-docker:latest`
- OR! run the container using the `docker-compose` orchestration script, from the project root: `docker-compose -f dev_environment/docker-compose-ubunty-sysbox.yml up -d`
  - And attach: `docker attach dev_environment_ubunty-sysbox_1`
- Once in the container, install python: `pyenv install 3.9.7`.
