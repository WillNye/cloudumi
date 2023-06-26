variable "account_id" {
  description = "The account id that this infrastructure is built in"
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
    condition     = contains(["development_2/development_2_admin", "global_tenant_data_staging/global_tenant_data_staging_admin", "global_tenant_data_prod/global_tenant_data_prod_admin"], var.profile)
    error_message = "Allowed AWS_PROFILEs are \"global_tenant_data_staging/global_tenant_data_staging_admin\" and \"global_tenant_data_prod/global_tenant_data_prod_admin\"."
  }
}

variable "region" {
  type    = string
  default = "us-west-2"

  validation {
    condition     = contains(["us-west-2"], var.region)
    error_message = "Allowed values for input_parameter are \"us-west-2\"."
  }
}

variable "stage" {
  type    = string
  default = "staging"

  validation {
    condition     = contains(["staging", "test", "dev", "prod"], var.stage)
    error_message = "Allowed values for input_parameter are \"staging\", \"test\", \"dev\", or \"prod\"."
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
