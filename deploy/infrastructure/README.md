# NOQ Infrastructure

Each NOQ infrastructure is setup in its own tenant and AWS account. When needed, a new deployment configuration tfvars
is added to the `live` directory under the new tenant id. Use this only to setup a new account backend infrastructure
and to update the infrastructure when changes are needed.

**NOTE**: it is imperative you enter the correct workspace using `terraform workspace select` before attempting to
update prod or production environments!

**NOTE**: currently all configuration files (.yaml, .yml) need to be updated manually after running terraform deploy or updates. The requisite outputs that are needed to update the `live` configuration files, use the `terraform output` command with the appropiate workspace (`terraform workspace select noq.dev-prod-1` for instance)

## Pre-requisites:

- AWS keys configured in ~/.aws/credentials - see the `AWS Credentials` section below
- terraform
- ecs-cli
- `yarn build_template` was run in the `frontend` folder

## Quick Start

Ensure that your AWS profile is setup correctly in the `~/.aws/credentials` file - the expectation is that there is a
`noq_dev` entry with AWS keys configured; this is the profile that terraform will look for explicitly.

- Ensure you have the pre-requisites installed
- Export your AWS Profile (see the `AWS Credentials` section below): `export AWS_PROFILE=noq_dev`

## Terraform

Terraform is only required when either establishing a new tenant / account or updating a current account. Each Terraform deployment is governed by a set of modules and environment specific tfvars (under the live folder hierarchy). See the `Structure` section below for a more detailed explanation.

To use terraform, follow the below steps:

- Ensure `AWS_PROFILE` is set to respective environment (`noq_dev` or `noq_prod`)
- Ensure `AWS_REGION` is set correctly (`us-west-2` for most clusters)
- Initialize Terraform if you haven't already: `terraform init`
- Setup your workspaces: `./setup.sh`
- Select the appropriate workspace: `terraform workspace select demo.noq.dev-prod-1` (for instance)
- For the first time, initialize the environment: `terraform init`
- Plan: `terraform plan --var-file=live/demo.noq.dev/prod-1/demo.noq.dev-prod.tfvars`
- Apply: `terraform apply --var-file=live/demo.noq.dev/prod-1/demo.noq.dev-prod.tfvars`
- Create the NOQ configuration files in the corresponding `live` configuration folder: `terraform output -json | bazel run //util/terraform_config_parser ~/dev/noq/cloudumi/deploy/infrastructure/live/noq.dev/shared/prod-1/` -- see the `terraform_config_parser` section below
- Destroy: `terraform destroy --var-file=live/demo.noq.dev/prod-1/demo.noq.dev-prod.tfvars`
- Get outputs: `terraform output`
- Refresh: `terraform refresh`

### terraform_config_parser

We provide a script that automatically generates (from templates) the product configuration files by parsing the Terraform output files. The script itself lives in the util/terrafom_config_parser directory in the mono repo and performs the following steps:

The way to execute this script is by piping the terraform output in JSON format into the script's STDIN: `terraform output -json | bazel run //util/terraform_config_parser <output_path_to_live_config_folder>`

Examples for the `<output_path_to_live_config_folder>`:

- ~/dev/noq/cloudumi/deploy/infrastructure/live/shared/prod-1
- ~/dev/noq/cloudumi/deploy/infrastructure/live/shared/prod-1
- ~/dev/noq/cloudumi/deploy/infrastructure/live/demo/prod-1

Note: in order for this to work, there are two pre-requisites:

1. The

- Uses the exported AWS_PROFILE to push the configuration.yaml file to S3 to the following location: `s3://noq.tenant-configuration-store/<namespace>/<stage>.<attributes>.config.yaml`
- Parse terraform output and writes the `live/<namespace>/<stage/attributes>/BUILD` file
- Parse terraform output and writes the `live/<namespace>/<stage/attributes>/compose.yaml` file
- Parse terraform output and writes the `live/<namespace>/<stage/attributes>/configuration.yaml` file
- Parse terraform output and writes the `live/<namespace>/<stage/attributes>/ecs.yaml` file

## Structure

- `live`: has configuration tfvars for each tenant that is instantiated
  - Each tenant should be stored in it's own directory using the form: `shared/`, if using the noq.dev domain. Otherwise tenant configuration should be stored under `<company_name>`.
  - This **only** applies to those companies that _require their own separate environment_. This **does not** apply to companies that are using the `noq.dev` shared environment that is managed by CloudUmi.
  - Tenants can be destroyed as well; tenant configuration should be retained for historical records
- `modules`: has all infrastucture as code modules
  - `services`: has services to be configured for deployment
    - `dynamo`: the table configurations
    - `elasticache`: the redis table
    - `s3`: the bucket to be used for configuration

## AWS Credentials

The ~/.aws/credentials file is expected to be in the following format to align with Terraform's deployment scripts:

```bash
[noq_dev]
aws_access_key_id = <DEV KEY>
aws_secret_access_key = <DEV SECRET>
[noq_prod]
aws_access_key_id = <PROD KEY>
aws_secret_access_key = <PROD SECRET>
```

Note specifically the `noq_dev` and `noq_prod` sections. Proper naming is critical to have a successful deployment.

# Deploy to prod automation

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com` (this authenticates your AWS PROFILE to ECR for registry upload purposes; hence the authentication via docker login)
- Reference `Terraform` section above on how to deploy / update terraform infrastructure (should be seldom)
- Optionally check all available build targets for `prod-1`: `bazelisk query //deploy/infrastructure/live/shared/...`
- Optionally push containers (at least the first time and anytime they change): `bazelisk run //deploy/infrastructure/live/shared/prod-1:api-container-deploy-prod; bazelisk run //deploy/infrastructure/live/shared/prod-1:celery-container-deploy-prod`
- Deploy: `bazelisk run //deploy/infrastructure/live/shared/prod-1`
- For convenience, run the `deploy/infrastructure/live/shared/staging-1/push_all_the_things.sh` script

# Deploy to production automation

- Set AWS_PROFILE: `export AWS_PROFILE=noq_prod`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 940552945933.dkr.ecr.us-west-2.amazonaws.com`
- Optionally check all available build targets for `prod-1`: `bazelisk query //deploy/infrastructure/live/shared/...`
- Optionally push containers (at least the first time and anytime they change): `bazelisk run //deploy/infrastructure/live/shared/prod-1:api-container-deploy-prod; bazelisk run //deploy/infrastructure/live/shared/prod-1:celery-container-deploy-prod`
- Deploy: `bazelisk run //deploy/infrastructure/live/shared/prod-1`
- For convenience, run the `deploy/infrastructure/live/shared/prod-1/push_all_the_things.sh` script

# Deploy to isolated clusters

- Understand the environment: does the isolated cluster have staging and prod? Just prod? Select the AWS_PROFILE appropriately
- Set AWS_PROFILE: `export AWS_PROFILE=noq_prod` - this is assuming we are looking to update their prod-1 part in their cluster
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 940552945933.dkr.ecr.us-west-2.amazonaws.com`
- Optionally check all available build targets for `prod-1`: `bazelisk query //deploy/infrastructure/live/cyberdyne/...` - note: using `cyberdyne` for this example, replace cyberdyne with <company name>
- Optionally push containers (at least the first time and anytime they change): `bazelisk run //deploy/infrastructure/live/cyberdyne/prod-1:api-container-deploy-prod; bazelisk run //deploy/infrastructure/live/cyberdyne/prod-1:celery-container-deploy-prod`
- Deploy: `bazelisk run //deploy/infrastructure/live/cyberdyne/prod-1`
- For convenience, run the `deploy/infrastructure/live/cyberdyne/prod-1/push_all_the_things.sh` script

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule
- SAAS-93: Secure private net
- SAAS-94: Convert the bazel build system to be entirely hermetic
- SAAS-95: Fix xmlsec in Bazel directed API build
- SAAS-96: Fix uvloop in Bazel directed API build

# Remove a cluster

- Set AWS_PROFLE: `export AWS_PROFILE=noq_dev` (or noq_prod)
- For prod: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/prod-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_dev`
- For production: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/prod-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_prod`
- Reference the `Terraform` section for more information on how to destroy an environment, if needed (in most cases it won't be)

# How to use ecs-cli to circumvent Bazel

Sometimes it is necessary to experiment with the ECS compose jobs. In those scenarios, the best way to get around the Bazel build targets is to start in a `live` configuration folder (for instance: `deploy/infrastructure/liv/noq.dev/shared/staging-1`). The compose.yaml file and the ecs.yaml file will be require to manipulate the cluster. Furthermore, you will need to set the requisite `AWS_PROFILE` environment variable (using something like `export AWS_PROFILE="noq_dev"` for instance).

- To create a service with containers (and to circumvent the load balancer configuration): `ecs-cli compose -f compose.yaml --cluster-config noq-dev-shared-staging-1 --ecs-params ecs.yaml -p noq-dev-shared-staging-1 --task-role-arn arn:aws:iam::259868150464:role/noq-dev-shared-staging-1-ecsTaskRole --region us-west-2 service up --create-log-groups --timeout 15`
  - This can be useful when making manual changes to the configuration file (either compose.yaml or ecs.yaml)
  - See below for the accompanying `ecs-cli compose service rm` call to remove the service
- To remove a service: `ecs-cli compose -p noq-dev-shared-staging-1 -f compose.yaml service rm`
- Reference: [ECS-CLI reference](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_reference.html)

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
