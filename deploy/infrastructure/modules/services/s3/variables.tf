variable "account_id" {
  description = "AWS account ID of this account"
  type        = string
}

variable "attributes" {
  description = "Additional attributes, e.g. `1`"
  type        = number
  default     = 1
}

variable "bucket_encryption_key" {
  description = "KMS key"
  type        = string
}

variable "bucket_name_prefix" {
  description = "The prefix to use for the S3 bucket name. This will be used to create the S3 bucket name. The bucket name will be the prefix + cluster ID."
  type        = string
  default     = "cloudumi-cache"
}

variable "lb_bucket_name_prefix" {
  description = "The prefix to use for the S3 bucket name. This will be used to create the S3 bucket name. The bucket name will be the prefix + cluster ID."
  type        = string
  default     = "cloudumi-lb"
}

variable "cluster_id" {
  description = "The cluster ID for CloudUmi."
  type        = string
}

variable "log_expiry" {
  description = "The number of days to keep logs for."
  type        = number
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
