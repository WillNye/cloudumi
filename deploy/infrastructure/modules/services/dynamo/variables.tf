variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type        = number
  default     = 1
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "dynamo_table_replica_regions" {
  description = "List of regions to replicate all DDB tables into"
  type        = list(any)
}

variable "noq_core" {
  type    = bool
  default = false
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck"
  type        = string
}

variable "cloudumi_resource_cache_multitenant_v2_tenant-arn-index_write_capacity" {
  description = "Write capacity for tenant-arn-index global secondary index on cloudumi_resource_cache_multitenant_v2"
  type        = number
  default     = 5
}

variable "cloudumi_resource_cache_multitenant_v2_tenant-index_write_capacity" {
  description = "Write capacity for tenant-index global secondary index on cloudumi_resource_cache_multitenant_v2"
  type        = number
  default     = 1
}