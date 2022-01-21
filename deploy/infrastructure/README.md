# NOQ Infrastructure

Each NOQ infrastructure is setup in its own tenant and AWS account. When needed, a new deployment configuration tfvars
is added to the `live` directory under the new tenant id. Use this only to setup a new account backend infrastructure
and to update the infrastructure when changes are needed.

**NOTE**: it is imperative you enter the correct workspace using `terraform workspace select` before attempting to
update staging or production environments!

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
- Deploy TF: `bazelisk run //deploy/infrastructure/live/noq.dev:tf-staging`
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev:staging`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule

# Deploy to production automation

## Quick Start

- Set AWS_PROFILE: `export AWS_PROFILE=noq_dev`
- Authenticate: `aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com`
- Deploy TF: `bazelisk run //deploy/infrastructure/live/noq.dev:tf-production`
- Deploy: `bazelisk run //deploy/infrastructure/live/noq.dev:production`

## Technical Debt

- Instead of using the genrule, build a bzl starlark rule

# Remove a tenant
Tenants can be destroyed after all ECS containers have been destroyed. Use either `ecscli` or the AWS UX to accomplish this.

After cleaning up the ECS environment, one can use `terraform destroy` to tear down the tenant, reference the `Quick Start` section on terraform above