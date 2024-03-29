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
  tags = merge(
    var.tags,
    {
      "System" : "Registration",
    }
  )
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
  name                       = "${var.cluster_id}-registration-response-queue"
  delay_seconds              = 90
  max_message_size           = 2048
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 300
  tags = merge(
    var.tags,
    {
      "System" : "RegistrationResponse",
    }
  )
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

resource "aws_sqs_queue" "github_app_noq_webhook" {
  name                      = "${var.cluster_id}-github-app-noq-webhook"
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.github_app_noq_webhook_deadletter.arn
    maxReceiveCount     = 4
  })

}

resource "aws_sns_topic_subscription" "github_app_noq_webhook" {
  topic_arn = "arn:aws:sns:${var.region}:${var.global_tenant_data_account_id}:github-app-noq-webhook"
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.github_app_noq_webhook.arn
}

resource "aws_sqs_queue_policy" "github_app_noq_webhook_queue_policy" {
  queue_url = aws_sqs_queue.github_app_noq_webhook.url

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "${var.cluster_id}-github_app_noq_webhook-policy",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.github_app_noq_webhook.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:sns:${var.region}:${var.global_tenant_data_account_id}:github-app-noq-webhook"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_sqs_queue" "github_app_noq_webhook_deadletter" {
  name = "${var.cluster_id}-github-app-webhook-dlq"
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = ["arn:aws:sqs:${var.region}:${var.account_id}:${var.cluster_id}-github-app-noq-webhook"]
  })
}
