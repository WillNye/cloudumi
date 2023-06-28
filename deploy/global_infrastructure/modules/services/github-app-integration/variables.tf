variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "lambda_function_name" {
  description = "function name"
  type        = string
  default     = "github_app_noq_webhook"
}

variable "github_app_noq_webhook_secret_arn" {
  description = "github_app_noq_webhook_secret_arn"
  type        = string
}