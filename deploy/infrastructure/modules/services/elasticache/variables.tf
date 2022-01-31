variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type    = number
  default = 1
}

variable "cluster_id" {
  type = string
  description = "The cluster ID for CloudUmi."
}

variable "noq_core" {
  type = bool
  default = false
}

variable "private_subnet_cidr_blocks" {
  description = "The CIDR blocks fo the private subnets to be used to filter ingress_cidr_blocks in the redis config"
  type = list(string)
}

variable "redis_cluster_access_sg_ids" {
  type = list(string)
  description = "Any security group ids that require access to the Redis cluster"
}

variable "redis_node_type" {
  type = string
  default = "cache.t3.small"
}

variable "subnet_ids" {
  description = "The subnet ids as generated"
  type = list(string)
}

variable "tags" {
  description = "The tag to assign to resources" 
  type = map(any)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck" 
  type = string
}

variable "vpc_id" {
  description = "The VPC ID as generated"
  type = string
}