variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type    = number
  default = 1
}

variable "cluster_id" {
  type = string
  description = "The cluster ID for CloudUmi."
}

variable "dynamo_table_replica_regions" {
  description = "List of regions to replicate all DDB tables into"
  type = list
}

variable "noq_core" {
  type = bool
  default = false
}

variable "tags" {
  description = "The tag to assign to resources"
  type = map(any)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck"
  type = string
}