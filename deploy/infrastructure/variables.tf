variable "allowed_inbound_cidr_blocks" {
  description = "The CIDR blocks that are allowed to connect to the cluster"
  type        = list(string)
  default     = []
}

variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type        = number
  default     = 1
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

variable "delimiter" {
  type        = string
  default     = "-"
  description = "Delimiter to be used between (1) `namespace`, (2) `name`, (3) `stage` and (4) `attributes`"
}

variable "domain_name" {
  type        = string
  description = "The specific domain name to be registered as the CNAME to the load balancer"
}

variable "dynamo_table_replica_regions" {
  description = "List of regions to replicate all DDB tables into"
  type        = list(any)
}

variable "lb_port" {
  description = "The port the load balancer will listen on."
  default     = 443
}

variable "namespace" {
  description = "Namespace, which could be your organization name. It will be used as the first item in naming sequence. The {namespace}.{zone} make up the domain name"
  type        = string
}

variable "noq_core" {
  description = "If set to true, then the module or configuration should only apply to NOQ core infrastructure"
  type        = bool
  default     = false
}

variable "profile" {
  description = "The AWS PROFILE, as configured in the file ~/.aws/credentials to be used for deployment"
  type        = string
  validation {
    condition     = contains(["noq_dev", "noq_prod"], var.profile)
    error_message = "Allowed AWS_PROFILEs are \"noq_dev\" and \"noq_prod\"."
  }
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
}

variable "tags" {
  description = "Any tags to assign to resources"
  type        = map(any)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck"
  type        = string
  default     = "3m"
}

variable "zone" {
  description = "The zone is the base part of the domain name. The {namespace}.{zone} make up the domain name"
  type        = string
  default     = "noq.dev"
}

variable "sentry_dsn" {
  description = "The Sentry DSN to use for logging exceptions"
  type        = string
}

variable "celery_log_level" {
  description = "The log level for Celery"
  type        = string
  default     = "DEBUG"
}

variable "celery_concurrency" {
  description = "The number of processes each celery worker should run to run"
  type        = string
  default     = "16"
}