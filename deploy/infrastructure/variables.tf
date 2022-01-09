variable "tf_profile" {
  type    = string
  default = "noq_dev"
}

variable "region" {
  type    = string
  default = "us-west-2"

  validation {
    condition     = contains(["us-west-1", "us-west-2"], var.region)
    error_message = "Allowed values for input_parameter are \"us-west-1\", \"us-west-2\"."
  }
}

variable "namespace" {
  type = string
  default = "noq"
}

variable "name" {
  type = string
  default = "common" 
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "attributes" {
  type = number
  default = 1
}

variable "capacity_providers" {
  description = "List of short names of one or more capacity providers to associate with the cluster. Valid values also include FARGATE and FARGATE_SPOT."
  type        = list(string)
  default     = ["FARGATE_SPOT", "FARGATE"]
}

variable "container_insights" {
  description = "Controls if ECS Cluster has container insights enabled"
  type        = bool
  default     = false
}

variable "noq_core" {
  type = bool
  default = false
}

variable "redis_node_type" {
  type = string
  default = "cache.t3.small"
}