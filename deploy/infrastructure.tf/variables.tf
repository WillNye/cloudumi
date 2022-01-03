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

variable "cluster_id" {
  type = string
  description = "The cluster ID for CloudUmi."
  default = "${namespace}-${name}-${stage}-${attributes}"
}
