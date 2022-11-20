variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type        = number
  default     = 1
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "region" {
  type        = string
  description = "The region that all services are deployed into"
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID"
  type        = string
}

variable "ecs_security_group_id" {
  description = "ECS security group ID"
  type        = list(string)
}

variable subnet_ids {
  description = "Subnet IDs"
  type        = list(string)
}

variable ecs_task_role_arn {
  description = "ECS task  role ARN"
  type        = string
}