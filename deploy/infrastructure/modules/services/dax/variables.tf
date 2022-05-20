variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "namespace" {
  description = "Namespace, which could be your organization name. It will be used as the first item in naming sequence. The {namespace}.{zone} make up the domain name"
  type        = string

  validation {
    condition     = length(var.namespace) <= 12
    error_message = "Tenant name must be shorter than 12 characters."
  }
}

variable "subnet_ids" {
  description = "The subnet ids as generated"
  type        = list(string)
}

variable "node_type" {
  type    = string
  default = "dax.t2.medium"
}

variable "node_count" {
  description = "Number of cluster nodes"
  type        = number
  default     = 3
}

variable "security_group_ids" {
  type        = list(string)
  default     = []
  description = "Any security group ids that require access to the cluster"
}
