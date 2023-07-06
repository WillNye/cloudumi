output "github_app_webhook_sns_topic_arn" {
  description = "Bucket for storing legal documentation"
  value       = aws_sns_topic.github_app_noq_webhook.arn
}

output "function_url" {
  value = aws_lambda_function_url.github_app_webhook.function_url
}