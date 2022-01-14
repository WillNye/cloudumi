variable "allowed_inbound_cidr_blocks" {
  description = "The CIDR blocks that are allowed to connect to the cluster"
  type        = list(string)
  default     = []
}

variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type    = number
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
  description = "If set to true, then the module or configuration should only apply to NOQ core infrastructure"
  type    = bool
  default = false
}

variable "private_subnet_cidrs" {
  description = "The CIDR block of the subnet the ConsoleMe server will be placed in."
  type        = list(string)
  default     = ["10.1.1.0/28"]
}

variable "public_subnet_cidrs" {
  description = "The CIDR block of the subnet the load balancer will be placed in."
  type        = list(string)
  default     = ["10.1.1.128/28", "10.1.1.144/28"] # LB requires at least two networks
}

variable "redis_node_type" {
  type    = string
  default = "cache.t3.small"
}

variable "region" {
  type    = string
  default = "us-west-2"

  validation {
    condition     = contains(["us-west-1", "us-west-2"], var.region)
    error_message = "Allowed values for input_parameter are \"us-west-1\", \"us-west-2\"."
  }
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
  description = "The availability zones to use for the subnets"
  type        = list(string)
  default     = []
}

variable "tf_profile" {
  type    = string
  default = "noq_dev"
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC."
  type        = string
  default     = "10.1.1.0/24"
}