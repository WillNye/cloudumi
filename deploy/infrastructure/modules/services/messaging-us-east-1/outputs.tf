
output "aws_marketplace_subscription_queue_arn" {
  description = "The SQS queue ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = join("", aws_sqs_queue.aws_marketplace_subscription_queue[*].arn)
}

output "aws_marketplace_subscription_queue_name" {
  description = "The SQS queue name that is used to trigger customer registration using the NOQ CF template"
  value       = join("", aws_sqs_queue.aws_marketplace_subscription_queue[*].name)
}