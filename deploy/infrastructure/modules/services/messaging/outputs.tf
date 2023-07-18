output "sns_registration_topic_arn" {
  description = "The SNS registration topic ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = aws_sns_topic.registration_topic.arn
}

output "sns_registration_topic_name" {
  description = "The SNS topic name that is used to trigger customer registration using the NOQ CF template"
  value       = aws_sns_topic.registration_topic.name
}

output "sqs_registration_queue_arn" {
  description = "The SQS registration queue ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = aws_sqs_queue.registration_queue.arn
}

output "sqs_registration_queue_url" {
  description = "The SQS registration queue URL that is used to trigger customer registration using the NOQ CF templates"
  value       = aws_sqs_queue.registration_queue.url
}

output "sqs_registration_queue_name" {
  description = "The SQS queue name that is used to trigger customer registration using the NOQ CF template"
  value       = aws_sqs_queue.registration_queue.name
}

output "sqs_registration_response_queue_arn" {
  description = "The SQS registration response queue ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = aws_sqs_queue.registration_response_queue.arn
}

output "sqs_registration_response_queue_name" {
  description = "The SQS response queue name that is used to trigger customer registration using the NOQ CF template"
  value       = aws_sqs_queue.registration_response_queue.name
}

output "sqs_github_app_noq_webhook_queue_arn" {
  description = "The SQS to see GitHub App Noq Webhook Events"
  value       = aws_sqs_queue.github_app_noq_webhook.arn
}

output "sqs_github_app_noq_webhook_queue_url" {
  description = "The SQS URL to see GitHub App Noq Webhook Events"
  value       = aws_sqs_queue.github_app_noq_webhook.url
}
