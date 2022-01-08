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