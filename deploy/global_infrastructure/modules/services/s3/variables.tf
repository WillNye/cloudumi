variable "bucket_name_prefix" {
  description = "The prefix to use for the S3 bucket name. This will be used to create the S3 bucket name. The bucket name will be the prefix + cluster ID."
  type        = string
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "s3_access_log_bucket" {
  description = "The S3 bucket to use for S3 access logs"
  type        = string
}