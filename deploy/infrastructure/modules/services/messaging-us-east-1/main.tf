terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.6.2" # specify the version you are using
    }
  }
}


resource "aws_sqs_queue" "aws_marketplace_subscription_queue" {
  count                     = var.aws_marketplace_subscription_sns_topic_arn != "" ? 1 : 0
  name                      = "${var.cluster_id}-aws_marketplace_subscription_queue"
  delay_seconds             = 5
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 20
  sqs_managed_sse_enabled   = true
  tags = merge(
    var.tags,
    {
      "System" : "AWSMarketplaceSubscriptionQueue",
    }
  )
}

resource "aws_sqs_queue_policy" "aws_marketplace_subscription_queue_policy" {
  count     = var.aws_marketplace_subscription_sns_topic_arn != "" ? 1 : 0
  queue_url = aws_sqs_queue.aws_marketplace_subscription_queue[count.index].id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : "*",
        "Action" : "sqs:SendMessage",
        "Resource" : aws_sqs_queue.aws_marketplace_subscription_queue[count.index].arn,
        "Condition" : {
          "ArnEquals" : {
            "aws:SourceArn" : var.aws_marketplace_subscription_sns_topic_arn
          }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "aws_marketplace_subscription_sns_subscription" {
  count     = var.aws_marketplace_subscription_sns_topic_arn != "" ? 1 : 0
  topic_arn = var.aws_marketplace_subscription_sns_topic_arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.aws_marketplace_subscription_queue[0].arn
}
