variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type    = number
  default = 1
}

variable "bucket_name_prefix" {
  description = "The prefix to use for the S3 bucket name. This will be used to create the S3 bucket name. The bucket name will be the prefix + cluster ID."
  type        = string
  default     = "cloudumi-cache"
}

variable "cluster_id" {
  description = "The cluster ID for CloudUmi."
  type        = string
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