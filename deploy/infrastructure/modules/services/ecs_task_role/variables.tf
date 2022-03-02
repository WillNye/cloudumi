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

variable "tenant_configuration_bucket_name" {
  description = "The tenant configuration bucket"
  type        = string
}