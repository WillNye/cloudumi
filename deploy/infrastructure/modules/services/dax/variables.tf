variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "tenant_name" {
  description = "The shortened name of the tenant"
  type        = string
  default     = "noq"

  validation {
    condition     = length(var.tenant_name) <= 12
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
