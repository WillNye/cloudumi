# NOQ Infrastructure

Each NOQ infrastructure is setup in its own tenant and AWS account. When needed, a new deployment configuration tfvars
is added to the `live` directory under the new tenant id. Use this only to setup a new account backend infrastructure
and to update the infrastructure when changes are needed.

**NOTE**: it is imperative you enter the correct workspace using `terraform workspace select` before attempting to
update staging or production environments!

**NOTE**: currently all configuration files (.yaml, .yml) need to be updated manually after running terraform deploy or updates. The requisite outputs that are needed to update the `live` configuration files, use the `terraform output` command with the appropiate workspace (`terraform workspace select noq.dev-staging-1` for instance)

## Pre-requisites:

- AWS keys configured in ~/.aws/credentials - see the `AWS Credentials` section below
- terraform
- ecs-cli

## Quick Start

Ensure that your AWS profile is setup correctly in the ~/.aws/credentials file - the expectation is that there is a
`noq_dev` entry with AWS keys configured; this is the profile that terraform will look for explicitly.

- Ensure you have the pre-requisites installed
- Export your AWS Profile (see the `AWS Credentials` section below): `export AWS_PROFILE=noq_dev`

## Terraform

Terraform is only required when either establishing a new tenant / account or updating a current account. Each Terraform deployment is governed by a set of modules and environment specific tfvars (under the live folder hierarchy). See the `Structure` section below for a more detailed explanation.

To use terraform, follow the below steps:

- Ensure `AWS_PROFILE` is set to respective environment (`noq_dev` or `noq_prod`)
- Initialize Terraform if you haven't already: `terraform init`
- Setup your workspaces: `./setup.sh`
- Select the appropriate workspace: `terraform workspace select demo.noq.dev-staging-1` (for instance)
- For the first time, initialize the environment: `terraform init`
- Plan: `terraform plan --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Apply: `terraform apply --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Create the NOQ configuration files in the corresponding `live` configuration folder: `terraform output -json | bazel run //util/terraform_config_parser ~/dev/noq/cloudumi/deploy/infrastructure/live/noq.dev/shared/staging-1/` -- see the `terraform_config_parser` section below
- Destroy: `terraform destroy --var-file=live/demo.noq.dev/staging-1/demo.noq.dev-staging.tfvars`
- Get outputs: `terraform output`
- Refresh: `terraform refresh`

### terraform_config_parser

We provide a script that automatically generates (from templates) the product configuration files by parsing the Terraform output files. The script itself lives in the util/terrafom_config_parser directory in the mono repo and performs the following steps:

The way to execute this script is by piping the terraform output in JSON format into the script's STDIN: `terraform output -json | bazel run //util/terraform_config_parser <output_path_to_live_config_folder>`

Examples for the `<output_path_to_live_config_folder>`:

- ~/dev/noq/cloudumi/deploy/infrastructure/live/noq.dev/shared/staging-1
- ~/dev/noq/cloudumi/deploy/infrastructure/live/noq.dev/shared/production-1
- ~/dev/noq/cloudumi/deploy/infrastructure/live/noq.dev/demo/staging-1

Note: in order for this to work, there are two pre-requisites:

1. The

- Uses the exported AWS_PROFILE to push the configuration.yaml file to S3 to the following location: `s3://noq.tenant-configuration-store/<zone>/<namespace>/<stage>.<attributes>.config.yaml`
- Parse terraform output and writes the `live/<zone>/<namespace>/<stage/attributes>/BUILD` file
- Parse terraform output and writes the `live/<zone>/<namespace>/<stage/attributes>/compose.yaml` file
- Parse terraform output and writes the `live/<zone>/<namespace>/<stage/attributes>/configuration.yaml` file
- Parse terraform output and writes the `live/<zone>/<namespace>/<stage/attributes>/ecs.yaml` file

## Structure

- `live`: has configuration tfvars for each tenant that is instantiated
  - Each tenant should be stored in it's own directory using the form: `noq.dev/<tenant name>`, if using the noq.dev domain. Otherwise tenant configuration should be stored under `<company_domain>/<tenant_name>`.
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

# Deploy to staging automation

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com` (this authenticates your AWS PROFILE to ECR for registry upload purposes; hence the authentication via docker login)
- Reference `Terraform` section above on how to deploy / update terraform infrastructure (should be seldom)
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/staging-1`

# Deploy to production automation

- Set AWS_PROFILE: `export AWS_PROFILE=noq_prod`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/production-1`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule
- SAAS-93: Secure private net
- SAAS-94: Convert the bazel build system to be entirely hermetic
- SAAS-95: Fix xmlsec in Bazel directed API build
- SAAS-96: Fix uvloop in Bazel directed API build

# Remove a tenant

- Set AWS_PROFLE: `export AWS_PROFILE=noq_dev` (or noq_prod)
- For staging: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/staging-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_dev`
- For production: `bazelisk run //deploy/infrastructure/live/noq.dev/shared/production-1:destroy --action_env=HOME=$HOME --action_env=AWS_PROFILE=noq_prod`
- Reference the `Terraform` section for more information on how to destroy an environment, if needed (in most cases it won't be)
