# NOQ Infrastructure

Each NOQ infrastructure is setup in its own tenant and AWS account. When needed, a new deployment configuration tfvars
is added to the `live` directory under the new tenant id. Use this only to setup a new account backend infrastructure
and to update the infrastructure when changes are needed.

**NOTE**: it is imperative you enter the correct workspace using `terraform workspace select` before attempting to
update staging or production environments!

**NOTE**: currently all configuration files (.yaml, .yml) need to be updated manually after running terraform deploy or updates. The requisite outputs that are needed to update the `live` configuration files, use the `terraform output` command with the appropiate workspace (`terraform workspace select noq.dev-staging-1` for instance)

## Pre-requisites:

- AWS keys configured in ~/.aws/credentials
- terraform
- ecs-cli

## Quick Start

Ensure that your AWS profile is setup correctly in the ~/.aws/credentials file - the expectation is that there is a
`noq_dev` entry with AWS keys configured; this is the profile that terraform will look for explicitly.

- Ensure you have the pre-requisites installed
- Export your AWS Profile if you're using one: `export AWS_PROFILE=noq_dev`
- Initialize Terraform if you haven't already: `terraform init`
- Setup your workspaces: `./setup.sh`
- Select the appropriate workspace: `terraform workspace select demo.noq.dev-staging-1` (for instance)
- For the first time, initialize the environment: `terraform init`
- Plan: `terraform plan --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Apply: `terraform apply --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Destroy: `terraform destroy --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Get outputs: `terraform output`
- Refresh: `terraform refresh`

## Structure

- `live`: has configuration tfvars for each tenant that is instantiated
  - Each tenant should be stored in it's own directory using the form: `<tenant name>.noq.dev`, which should echo the tenant access URI
  - Updates can be achieved in the same way
  - Tenants can be destroyed as well; tenant configuration should be retained for historical records
- `modules`: has all infrastucture as code modules
  - `services`: has services to be configured for deployment
    - `dynamo`: the table configurations
    - `elasticache`: the redis table
    - `s3`: the bucket to be used for configuration

# Deploy to staging automation

## Quick Start

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`
- Reference Terraform section on how to deploy / update terraform infrastructure (should be seldom)
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev/staging-1`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule

# Deploy to production automation

## Quick Start

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev/production-1`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule

# Remove a cluster

- Set AWS_PROFLE: `export AWS_PROFILE=noq_dev` (or noq_prod)
- For staging: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/staging-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_dev`
- For production: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/prod-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_prod`
- Reference the `Terraform` section for more information on how to destroy an environment, if needed (in most cases it won't be)

# How to use ecs-cli to circumvent Bazel
Sometimes it is necessary to experiment with the ECS compose jobs. In those scenarios, the best way to get around the Bazel build targets is to start in a `live` configuration folder (for instance: `deploy/infrastructure/liv/noq.dev/shared/staging-1`). The compose.yaml file and the ecs.yaml file will be require to manipulate the cluster. Furthermore, you will need to set the requisite `AWS_PROFILE` environment variable (using something like `export AWS_PROFILE="noq_dev"` for instance).

* To create a service with containers (and to circumvent the load balancer configuration): `ecs-cli compose -f compose.yaml --cluster-config noq-dev-shared-staging-1 --ecs-params ecs.yaml -p noq-dev-shared-staging-1 --task-role-arn arn:aws:iam::259868150464:role/noq-dev-shared-staging-1-ecsTaskRole --region us-west-2 service up --create-log-groups --timeout 15`
  * This can be useful when making manual changes to the configuration file (either compose.yaml or ecs.yaml)
  * See below for the accompanying `ecs-cli compose service rm` call to remove the service
* To remove a service: `ecs-cli compose -p noq-dev-shared-staging-1 -f compose.yaml service rm`
* Reference: [ECS-CLI reference](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_reference.html)

# How to manually build and deploy the containers
- Build/push API container: `bazelisk run //api:container; bazelisk run //api:container_deploy_staging`
- Build/push Celery container: `bazelisk run //common/celery_tasks:container; bazelisk run //common/celery_tasks:container_deploy_staging` 

# Troubleshooting
## Error creating service... draining
```
ERRO[0001] Error creating service                        error="InvalidParameterException: Unable to Start a service that is still Draining." service=noq-dev-shared-staging-1
INFO[0001] Created an ECS service                        service=noq-dev-shared-staging-1 taskDefinition="noq-dev-shared-staging-1:18"
FATA[0001] InvalidParameterException: Unable to Start a service that is still Draining. 
```

This happens when a service is removed and recreated too quickly. It'll take a few minutes between teardown and setup.
