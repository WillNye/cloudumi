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
