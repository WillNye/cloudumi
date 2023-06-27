output "github_app_webhook_sns_topic_arn" {
  description = "Bucket for storing legal documentation"
  value       = aws_sns_topic.github_app_noq_webhook.arn
}