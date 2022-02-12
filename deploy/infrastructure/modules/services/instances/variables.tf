variable "allowed_inbound_cidr_blocks" {
  description = "Allowed inbound CIDRs for the security group rules."
  type        = list(string)
}

variable "cluster_id" {
  description = "The cluster ID for CloudUmi."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnets ids"
  type        = list(string)
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "vpc_id" {
  description = "The VPC ID"
  type        = string
}