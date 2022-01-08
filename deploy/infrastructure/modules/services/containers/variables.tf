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
  type = string
  description = "The cluster ID for CloudUmi."
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "noq_core" {
  type = bool
  default = false
}