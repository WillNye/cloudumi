variable "account_id" {
  description = "The account id that this infrastructure is built in"
  type        = string
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "global_tenant_data_account_id" {
  description = "Account ID of the AWS Tenant Data Account"
  type        = string
}

variable "region" {
  description = "deployed aws region"
  type        = string
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}
