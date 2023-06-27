variable "tags" {
  description = "The tag to assign to resources"
  type        = map(any)
}

variable "lambda_function_name" {
  description = "function name"
  type        = string
  default     = "github_app_webhook"
}