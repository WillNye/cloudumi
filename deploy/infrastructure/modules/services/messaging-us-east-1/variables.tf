variable "account_id" {
  description = "The account id that this infrastructure is built in"
  type        = string
}

variable "cluster_id" {
  type        = string
  description = "The cluster ID for CloudUmi."
}

variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "aws_marketplace_subscription_sns_topic_arn" {
  description = "The ARN of the Amazon-managed SNS topic for AWS Marketplace Subscriptions"
  type        = string
  default     = ""
}