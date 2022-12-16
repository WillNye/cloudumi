variable "cluster_id" {
  type        = string
  description = "The name of the RDS cluster."
}

variable "database_name" {
  type        = string
  description = "The name of the default db on the cluster."
}

variable "region" {
  type        = string
  description = "The region to deploy the RDS cluster to."
  default     = "us-west-1"
}

variable "private_subnet_cidr_blocks" {
  description = "The CIDR blocks fo the private subnets to be used to filter ingress_cidr_blocks"
  type        = list(string)
}

variable "rds_instance_count" {
  type    = number
  default = 1
}

variable "rds_instance_type" {
  type    = string
  default = "db.t4g.medium"
}

variable "subnet_ids" {
  description = "The subnet ids as generated"
  type        = list(string)
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "vpc_id" {
  description = "The VPC ID as generated"
  type        = string
}

variable "master_username" {
  type = string
}

variable "master_password" {
  type = string
}

variable "kms_key_id" {
  type = string
}
