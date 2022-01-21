variable "allowed_inbound_cidr_blocks" {
  description = "Allowed inbound CIDRs for the security group rules."
  default     = []
  type        = list(string)
}

variable "attributes" {
  description = "The attribute (ie. 1)"
  type = number
  default = 1
}

variable "capacity_providers" {
  description = "List of short names of one or more capacity providers to associate with the cluster. Valid values also include FARGATE and FARGATE_SPOT."
  type        = list(string)
  default     = ["FARGATE_SPOT", "FARGATE"]
}

variable "cluster_id" {
  description = "The cluster ID for CloudUmi."
  type = string
}

variable "container_insights" {
  description = "Controls if ECS Cluster has container insights enabled"
  type        = bool
  default     = false
}

variable "convert_case" {
  description = "Convert fields to lower case"
  default     = "true"
}

variable "default_tags" {
  description = "Default billing tags to be applied across all resources"
  type        = map(string)
  default     = {}
}

variable "delimiter" {
  type        = string
  default     = "-"
  description = "Delimiter to be used between (1) `namespace`, (2) `name`, (3) `stage` and (4) `attributes`"
}

variable "domain_name" {
  description = "The domain name that should be used to create the certificate"
  type = string
}

variable "lb_port" {
  description = "The port the load balancer will listen on."
  default     = 443
}

variable "name" {
  description = "A name to give to the cluster in the namespace; the name could be a department or evaluation or similar"
  type = string
  default = "common"
}

variable "namespace" {
  description = "Namespace, which could be your organization name. It will be used as the first item in naming sequence."
  type    = string
  default = "noq"
}

variable "noq_core" {
  type = bool
  default = false
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "subnet_azs" {
  description = "Subnets will be created in these availability zones (need at least two for load balancer)."
  type        = list(string)
}

variable "system_bucket" {
  description = "The bucket used for CloudUmi configuration and logs"
  type = string
}

variable "tags" {
  description = "The tag to assign to resources" 
  type = map(string)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck" 
  type = string
}