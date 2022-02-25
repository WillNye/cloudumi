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
AWS_PROFILE=noq_dev aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 259868150464.dkr.ecr.us-west-2.amazonaws.com
docker build -t cloudumi .
docker tag cloudumi:latest 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest
docker push 259868150464.dkr.ecr.us-west-2.amazonaws.com/cloudumi:latest
```

# ECS Staging instructions

AWS_PROFILE=noq_dev ecs-cli up --cluster-config noq-staging

# Terraform instructions

First, run `cd deploy/infrastructure`.

## Initialize Terraform with backend

AWS_PROFILE=noq_dev terraform init

## Plan the changes

AWS_PROFILE=noq_dev terraform plan -var-file="staging.tfvars"

## Apply the changes

AWS_PROFILE=noq_dev terraform apply -var-file="staging.tfvars"

# Github Actions

We use Github Actions for CI/CD automation, this is configured using the .github/workflows yaml configuration files.

## Testing locally

To test Github actions locally, we use the [act tool](https://github.com/nektos/act); a few important things to consider:

- Ensure you have your weep configuration in `/etc/weep/weep.yaml` just in case any bazel jobs are run. Bazel reassigns the `$HOME` variable in the sandbox, which means it will not be able to find `~/.weep/weep.yaml`.
- Add the --secret-file argument to `act`: `--secret-file .env_github_action_secrets`
- Specify what `runs-on` should run on locally (it's going to be configured for `self-hosted` in most if not all configurations): `-P self-hosted=nektos/act-environments-ubuntu:18.04`

To test a particular job: `act -P self-hosted=nektos/act-environments-ubuntu:18.04 --secret-file .env_github_action_secrets workflow_dispatch -j build` will dispatch all jobs that are named `build`
