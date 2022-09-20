# Overview

Covers every NOQ deployment aspect.

> Quick Start:

- Infrastructure:
  - [Overview](infrastructure/README.md)
  - [Terraform](infrastructure/README.md#terraform)
  - [Quick Start](infrastructure/README.md#quick-start)
  - [Github Actions]()
- Staging:
  - [Governing Configuration](infrastructure/live/shared/staging-1/noq.dev-staging.tfvars)
- Prod:
  - [Governing Configuration](infrastructure/live/shared/prod-1/noq.dev-prod.tfvars)
- Cyberdyne:
  - [Overview](infrastructure/live/cyberdyne/prod-1/README.md)
  - [Governing Configuraiton](infrastructure/live/cyberdyne/prod-1/cyberdyne.noq.dev-prod.tfvars)

# Easy Deploy

- Reference link: https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-west-2.amazonaws.com%2Fbc-cf-template-890234264427-prod%2Fread_only_template.yml&param_ExternalID=baf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=mattdaue-bridgecrew-read&param_ResourceNamePrefix=mattdaue-bc-read&param_CustomerName=mattdaue
- NOQ link (mattdaue): https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-east-1.amazonaws.com%2Fcloudumi-cf-templates%2Fiam_stack_ecs.cf.yaml&param_ExternalID=baf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=mattdaue-cloudumi-iam&param_ResourceNamePrefix=mattdaue-cloudumi-iam&param_CustomerName=mattdaue
- NOQ link (ccastrapel): https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?templateURL=https%3A%2F%2Fs3.us-east-1.amazonaws.com%2Fcloudumi-cf-templates%2Fiam_stack_ecs.cf.yaml&param_ExternalID=caf62b81-52ea-4e75-8fb5-6428d586af3f&stackName=ccastrapel-cloudumi-iam&param_ResourceNamePrefix=ccastrapel-cloudumi-iam&param_CustomerName=ccastrapel

## Central Role

- Execute `./deploy_central_role.sh` with AWS_PROFILE of your choice (for dev purposes only)

# Upload docker image to ECR manually

## Login to ECR

```bash
AWS_PROFILE=noq_staging aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com
docker build -t cloudumi .
docker tag cloudumi:latest 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest
docker push 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest
```

# ECS Staging instructions

AWS_PROFILE=noq_staging ecs-cli up --cluster-config noq-staging

# Terraform instructions

First, run `cd deploy/infrastructure`.
then `export AWS_PROFILE=noq_staging`

## Initialize Terraform with backend

terraform init

## Plan the changes

terraform plan -var-file="staging.tfvars"

## Apply the changes

terraform apply -var-file="staging.tfvars"

# Github Actions

We use Github Actions for CI/CD automation, this is configured using the .github/workflows yaml configuration files.

## Testing locally

To test Github actions locally, we use the [act tool](https://github.com/nektos/act); a few important things to consider:

- Ensure you have your weep configuration in `/etc/weep/weep.yaml` just in case any bazel jobs are run. Bazel reassigns the `$HOME` variable in the sandbox, which means it will not be able to find `~/.weep/weep.yaml`.
- Add the --secret-file argument to `act`: `--secret-file .env_github_action_secrets`
- Specify what `runs-on` should run on locally (it's going to be configured for `self-hosted` in most if not all configurations): `-P self-hosted=nektos/act-environments-ubuntu:18.04`

To test a particular job: `act -P self-hosted=nektos/act-environments-ubuntu:18.04 --secret-file .env_github_action_secrets workflow_dispatch -j build` will dispatch all jobs that are named `build`

# Publish to Staging

Publishing to staging is a build target that utilizes a genrule syntax to deploy containers via the `ECS-CLI` tool. Make sure that you have the tool installed - see `Installing ECS-CLI`.

- `bazelisk run //deploy/infrastructure/live/shared/staging-1:staging-1`

Note: there is a script that is templated in the terraform config parser package, called `push_all_the_things.sh`, which has an anti-dote called `revert_all_the_things.sh`.

To deploy to staging, simply run this script:

- `deploy/infrastructure/live/shared/staging-1/push_all_the_things.sh`

# Publish to Prod

> Do you really want this? Do you have access?

- `bazelisk run //deploy/infrastructure/live/shared/prod-1:prod-1`

Note: there is a script that is templated in the terraform config parser package, called `push_all_the_things.sh`, which has an anti-dote called `revert_all_the_things.sh`.

To deploy to production, simply run this script:

- `deploy/infrastructure/live/shared/prod-1/push_all_the_things.sh`

# Revert Staging

Sometimes S\*\*\* happens.

To revert: `bazelisk run //deploy/infrastructure/live/shared/staging-1:ecs_undeployer` or `deploy/infrastructure/live/shared/staging-1/revert_all_the_things.sh`

Notice: the above command, run without argument, will automatically find the previous version. Sometimes it is more desirable to target a specific version. In that case use the `ROLLBACK_VERSION` environment variable:
`ROLLBACK_VERSION=1.2.3 bazelisk run //deploy/infrastructure/live/shared/staging-1:ecs_undeployer` or `ROLLBACK_VERSION=1.2.3 deploy/infrastructure/live/shared/staging-1/revert_all_the_things.sh`.

# Revert Prod

Sometimes S\*\*\* happens. Hopefully this will never be your nightmare...

To revert: `bazelisk run //deploy/infrastructure/live/shared/prod-1:ecs_undeployer` or `deploy/infrastructure/live/shared/prod-1/revert_all_the_things.sh`

Notice: the above command, run without argument, will automatically find the previous version. Sometimes it is more desirable to target a specific version. In that case use the `ROLLBACK_VERSION` environment variable:
`ROLLBACK_VERSION=1.2.3 bazelisk run //deploy/infrastructure/live/shared/prod-1:ecs_undeployer` or `ROLLBACK_VERSION=1.2.3 deploy/infrastructure/live/shared/prod-1/revert_all_the_things.sh`.
