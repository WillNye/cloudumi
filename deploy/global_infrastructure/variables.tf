variable "account_id" {
  description = "The account id that this infrastructure is built in"
  type        = string
}

variable "github_app_noq_webhook_secret_arn" {
  description = "github_app_noq_webhook_secret_arn"
  type        = string
}

variable "domain_name" {
  type        = string
  description = "The specific domain name to be registered as the CNAME to the load balancer"
}

variable "dynamo_table_replica_regions" {
  description = "List of regions to replicate all DDB tables into"
  type        = list(any)
}

variable "profile" {
  description = "The AWS PROFILE, as configured in the file ~/.aws/credentials to be used for deployment"
  type        = string
  validation {
    condition     = contains(["development/development_admin", "noq_global_staging", "noq_global_prod"], var.profile)
    error_message = "Allowed AWS_PROFILEs are \"noq_global_staging\" and \"noq_global_prod\"."
  }
}

variable "region" {
  type    = string
  default = "us-west-2"

  validation {
    condition     = contains(["us-west-1", "us-west-2"], var.region)
    error_message = "Allowed values for input_parameter are \"us-west-1\", \"us-west-2\"."
  }
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["dev", "staging", "test", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", or \"prod\"."
  }
}

variable "tags" {
  description = "Any tags to assign to resources"
  type        = map(any)
}

variable "s3_access_log_bucket" {
  description = "The S3 bucket to store S3 access logs in"
  type        = string
}
