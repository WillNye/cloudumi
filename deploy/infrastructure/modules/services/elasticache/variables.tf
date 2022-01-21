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

variable "redis_node_type" {
  type = string
  default = "cache.t3.small"
}

variable "tags" {
  description = "The tag to assign to resources" 
  type = map(string)
}

variable "timeout" {
  description = "The timeout for each resource that may get stuck" 
  type = string
}