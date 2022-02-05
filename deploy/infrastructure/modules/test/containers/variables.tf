variable "ecs_cluster_name" {
  description = "The ecs test cluster is an output of the main deploy terraform setup"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "The task IAM execution role"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "The task IAM role"
  type        = string
}

variable "profile" {
  description = "The AWS profile to select from your .aws/credentials file"
  type        = string
}

variable "region" {
  description = "The region set as per the output"
  type        = string
}

variable "security_groups" {
  description = "List of security groups associated to this service"
  type        = list(string)
}

variable "stage" {
  description = "The stage set as per the output"
  type        = string
}

variable "subnets" {
  description = "Associated subnets"
  type        = list(string)
}