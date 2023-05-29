variable "allowed_inbound_cidr_blocks" {
  description = "Allowed inbound CIDRs for the security group rules."
  type        = list(string)
}

variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type        = number
  default     = 1
}

variable "cloudumi_temp_files_bucket" {
  description = "Bucket for storing temporary files"
  type        = string
}

variable "bucket_encryption_key" {
  description = "KMS key used to encrypt bucket objects"
  type        = string
}

variable "container_insights" {
  description = "Controls if ECS Cluster has container insights enabled"
  type        = bool
  default     = false
}

variable "capacity_providers" {
  description = "List of short names of one or more capacity providers to associate with the cluster. Valid values also include FARGATE and FARGATE_SPOT."
  type        = list(string)
  default     = ["FARGATE_SPOT", "FARGATE"]
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "lb_port" {
  description = "The port the load balancer will listen on."
  default     = 443
}

variable "load_balancer_sgs" {
  description = "Any load balancer that requires access to the services should be added here"
  type        = list(string)
}

variable "namespace" {
  description = "Namespace, which could be your organization name. It will be used as the first item in naming sequence. The {namespace}.{zone} make up the domain name"
  type        = string
}

variable "noq_core" {
  type    = bool
  default = false
}

variable "region" {
  type        = string
  description = "The region that all services are deployed into"
}

variable "registration_queue_arn" {
  description = "The registration queue ARN for the registration workflow"
  type        = string
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "subnet_ids" {
  description = "The subnet ids as generated"
  type        = list(string)
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "tenant_configuration_bucket_name" {
  description = "The tenant configuration bucket"
  type        = string
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck"
  type        = string
}

variable "vpc_cidr_range" {
  description = "VPC CIDR Range"
  type        = string
}
variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "cloudumi_files_bucket" {
  description = "The S3 bucket to store cached data for tenants"
  type        = string
}

variable "aws_secrets_manager_cluster_string" {
  sensitive   = true
  description = "The YAML-encoded AWS Secrets Manager secret"
  type        = string
}