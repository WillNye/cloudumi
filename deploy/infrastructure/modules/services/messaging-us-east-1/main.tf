terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.34.0" # specify the version you are using
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
  tags = merge(
    var.tags,
    {
      "System" : "AWSMarketplaceSubscriptionQueue",
    }
  )
}

resource "aws_sns_topic_subscription" "aws_marketplace_subscription_sns_subscription" {
  count     = var.aws_marketplace_subscription_sns_topic_arn != "" ? 1 : 0
  topic_arn = var.aws_marketplace_subscription_sns_topic_arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.aws_marketplace_subscription_queue[0].arn
}