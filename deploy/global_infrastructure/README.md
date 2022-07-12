# NOQ Global Infrastructure

NOQ Global infrastructure is...well...global so it's used across all tenants and AWS accounts.
As a result, there is a slightly different process for deploying.

**NOTE**: it is imperative you enter the correct workspace using `terraform workspace select` before attempting to
update prod or production environments!

**NOTE**: currently all configuration files (.yaml, .yml) need to be updated manually after running terraform deploy or updates. The requisite outputs that are needed to update the `live` configuration files, use the `terraform output` command with the appropiate workspace (`terraform workspace select shared-prod-1` for instance)

**NOTE**: the ecs task role is incredibly important - once created it should **never** be deleted. This is why there is a special variable that is called `modify_ecs_task_role`, which should always be set to false. Once set to true, it allows modification, to include deletions of the variable.
The only time the variable should be set to true is upon initial cluster creation - this is to ensure that the ecs task role is created.

## Pre-requisites:

- AWS keys configured in ~/.aws/credentials - see the `AWS Credentials` section below
- terraform

## Quick Start

Ensure that your AWS profile is setup correctly in the `~/.aws/credentials` file - the expectation is that there is a
`noq_global_staging` and `noq_global_prod` entry with AWS keys configured; this is the profile that terraform will look for explicitly.

- Ensure you have the pre-requisites installed
- Export your AWS Profile (see the `AWS Credentials` section below): `export AWS_PROFILE=noq_global_staging`

## Terraform

### Cheat Codes

#### Staging

export AWS_PROFILE=noq_global_staging AWS_REGION=us-west-2
terraform workspace select shared-staging-global
terraform refresh --var-file=live/shared/staging-global/noq.dev-staging.tfvars
terraform plan --var-file=live/shared/staging-global/noq.dev-staging.tfvars
terraform apply --var-file=live/shared/staging-global/noq.dev-staging.tfvars

#### Prod

export AWS_PROFILE=noq_global_prod AWS_REGION=us-west-2
terraform workspace select shared-prod-global
terraform refresh --var-file=live/shared/prod-global/noq.dev-prod.tfvars
terraform plan --var-file=live/shared/prod-global/noq.dev-prod.tfvars
terraform apply --var-file=live/shared/prod-global/noq.dev-prod.tfvars

Terraform is only required when either establishing a new tenant / account or updating a current account. Each Terraform deployment is governed by a set of modules and environment specific tfvars (under the live folder hierarchy). See the `Structure` section below for a more detailed explanation.

To use terraform, follow the below steps:

- Ensure `AWS_PROFILE` is set to respective environment (`noq_global_prod` or `noq_global_staging`)
- Ensure `AWS_REGION` is set correctly (`us-west-2` for most clusters)
- Initialize Terraform if you haven't already: `terraform init`
- Setup your workspaces: `./setup.sh`
- Select the appropriate workspace: `terraform workspace select shared-staging-global` (for instance)
- For the first time, initialize the environment: `terraform init --var-file=live/shared/staging-global/noq.dev-staging.tfvars`
- Plan: `terraform plan --var-file=live/shared/staging-global/noq.dev-staging.tfvars`
- Apply: `terraform apply --var-file=live/shared/staging-global/noq.dev-staging.tfvars`
- Create the NOQ configuration files in the corresponding `live` configuration folder: `terraform output -json | bazel run //util/terraform_config_parser ~/dev/noq/cloudumi` -- see the `terraform_config_parser` section below
- Destroy: `terraform destroy --var-file=live/shared/staging-global/noq.dev-staging.tfvars`
- Get outputs: `terraform output`
- Refresh: `terraform refresh`

### terraform_config_parser

Run on each AWS account for the updated environment. Use the `README` in `deploy/infrastructure`

## Structure

- `live`: has configuration tfvars for each tenant that is instantiated
  - Contains each supported environment. Currently, that is prod and staging.
- `modules`: has all infrastructure as code modules
  - `services`: has services to be configured for deployment
    - `dynamo`: the table configurations
    - `s3`: the bucket to be used for configuration

## AWS Credentials

The AWS SDK must be able to find updated credentials for the `noq_dev`, `noq_global_prod`, and `noq_global_staging` profiles.
The AWS SDK will attempt to find credentials from a number of locations. See the [AWS Default Credential Provider Chain](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/credentials.html#credentials-default) for more details.

Weep enables you to retrieve temporary 1 hour credentials from our Noq tenant (https://corp.noq.dev). Here
are the recommended avenues:

Option 1: Set your AWS Profile with `credential_process` to never think about credentials. This method is problematic
if you are running services in a container and the container doesn't have access to the Weep binary.
update your `~/.aws/config` file with the following:

```
[profile noq_global_prod]
credential_process = weep credential_process  arn:aws:iam::306086318698:role/global_tenant_data_prod_admin

[profile noq_global_staging]
credential_process = weep credential_process arn:aws:iam::615395543222:role/global_tenant_data_staging_admin
```

Option 2: To retrieve temporary 1 hour credentials from Noq for each profile, run the following commands:

```
weep file development_admin --profile noq_dev
weep file noq_global_prod --profile global_tenant_data_prod_admin
weep file noq_global_staging --profile global_tenant_data_staging_admin
```

Option 4: Weep can emulate the ECS credential provider locally. This method is much more performant than credential_process, and
it handles automatic credential refresh before your credentials expire. This method is extremely useful for long-lived operations:

Run `weep serve` in a separate terminal, or as a daemon

Then run the following commands (You can configure your IDE to use these settings):

```
export AWS_CONTAINER_CREDENTIALS_FULL_URI=http://localhost:9091/ecs/development_admin
aws sts get-caller-identity
```
