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