variable "bucket_encryption_key" {
  description = "KMS key used to encrypt bucket objects"
  type        = string
}

variable "cloudumi_files_bucket" {
  description = "The S3 bucket to store cached data for tenants"
  type        = string
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "modify_ecs_task_role" {
  type        = bool
  description = "If set, creates the ECS task role; otherwise it will expect the role to already exist"
}

variable "registration_queue_arn" {
  description = "The registration queue ARN for the registration workflow"
  type        = string
}

variable "github_app_noq_webhook_queue_arn" {
  description = "The github_app_noq_webhook_queue_arn queue ARN for the GitHub App Noq workflow"
  type        = string
}

variable "aws_marketplace_subscription_queue_arn" {
  description = "The aws_marketplace_subscription_queue_arn queue ARN for the AWS Marketplace subscription workflow"
  type        = string
}

variable "tenant_configuration_bucket_name" {
  description = "The tenant configuration bucket"
  type        = string
}

variable "aws_secrets_manager_arn" {
  description = "The ARN of the AWS Secrets Manager secret that contains the credentials for the tenant"
  type        = string
}

variable "noq_core" {
  type    = bool
  default = false
}