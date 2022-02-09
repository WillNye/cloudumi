resource "aws_sns_topic" "registration_topic" {
  name            = "${var.cluster_id}-registration-topic"
  delivery_policy = <<EOF
{
  "http": {
    "defaultHealthyRetryPolicy": {
      "minDelayTarget": 20,
      "maxDelayTarget": 20,
      "numRetries": 3,
      "numMaxDelayRetries": 0,
      "numNoDelayRetries": 0,
      "numMinDelayRetries": 0,
      "backoffFunction": "linear"
    },
    "disableSubscriptionOverrides": false,
    "defaultThrottlePolicy": {
      "maxReceivesPerSecond": 1
    }
  }
}
EOF
  tags = merge(
    var.tags,
    {
      "System" : "Registration",
    }
  )
}

resource "aws_sns_topic_policy" "registration_topic_policy" {
  arn = aws_sns_topic.registration_topic.arn

  policy = data.aws_iam_policy_document.registration_topic_policy_document.json
}

data "aws_iam_policy_document" "registration_topic_policy_document" {
  policy_id = "__registration_topic_policy"

  statement {
    sid = "AllowAccessToPublishFromAllAccounts"
    actions = [
      "SNS:Publish",
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    effect = "Allow"

    resources = [
      aws_sns_topic.registration_topic.arn,
    ]
  }

  statement {
    sid = "AllowAdditionalAccessInternally"
    actions = [
      "SNS:Subscribe",
      "SNS:SetTopicAttributes",
      "SNS:RemovePermission",
      "SNS:Receive",
      "SNS:Publish",
      "SNS:ListSubscriptionsByTopic",
      "SNS:GetTopicAttributes",
      "SNS:DeleteTopic",
      "SNS:AddPermission",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"

      values = [
        var.account_id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = [
      aws_sns_topic.registration_topic.arn,
    ]
  }
}

resource "aws_sqs_queue" "registration_queue" {
  name                      = "${var.cluster_id}-registration-queue"
  delay_seconds             = 90
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_sqs_queue_policy" "registration_queue_policy" {
  queue_url = aws_sqs_queue.registration_queue.url

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "${var.cluster_id}-registration-queue-policy",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.registration_queue.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_sns_topic.registration_topic.arn}"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_sqs_queue" "registration_response_queue" {
  name                      = "${var.cluster_id}-registration-response-queue"
  delay_seconds             = 90
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_sqs_queue_policy" "registration_response_queue_policy" {
  queue_url = aws_sqs_queue.registration_response_queue.url

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "${var.cluster_id}-registration-queue-policy",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.registration_response_queue.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_sns_topic.registration_topic.arn}"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_sns_topic_subscription" "registration_queue_subscription_to_registration_topic" {
  topic_arn = aws_sns_topic.registration_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.registration_queue.arn
}

resource "aws_sns_topic_subscription" "registration_response_queue_subscription_to_registration_topic" {
  topic_arn = aws_sns_topic.registration_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.registration_response_queue.arn
}