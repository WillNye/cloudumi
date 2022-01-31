variable "allowed_inbound_cidr_blocks" {
  description = "Allowed inbound CIDRs for the security group rules."
  type        = list(string)
}

variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type    = number
  default = 1
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
  type = string
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

variable "noq_core" {
  type = bool
  default = false
}

variable "region" {
  type = string
  description = "The region that all services are deployed into"
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
  type = list(string)
}

variable "tags" {
  description = "The tag to assign to resources" 
  type = map(any)
}

variable "test_access_sg_id" {
  description = "Test access on port 22" 
  type = string
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck" 
  type = string
}

variable "vpc_cidr_range" {
  description = "VPC CIDR Range"
  type = string
}
variable "vpc_id" {
  description = "VPC ID"
  type = string
}