variable "dynamo_table_replica_regions" {
  description = "List of regions to replicate all DDB tables into"
  type        = list(any)
  default     = []
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}