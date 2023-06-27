data "aws_organizations_organization" "owner" {}

data "aws_iam_policy_document" "sns_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "sns_failure_feedback" {
  name               = "GitHubSNSFailureFeedback"
  assume_role_policy = data.aws_iam_policy_document.sns_assume_role.json

  inline_policy {
    name = "my_inline_policy"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:PutMetricFilter",
            "logs:PutRetentionPolicy"
          ]
          Effect   = "Allow"
          Resource = "*"
        },
      ]
    })
  }
}

resource "aws_sns_topic" "github_app_noq_webhook" {
  name                          = "github-app-noq-webhook"
  sqs_failure_feedback_role_arn = aws_iam_role.sns_failure_feedback.arn

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_sns_topic_policy" "github_app_noq_webhook" {
  arn    = aws_sns_topic.github_app_noq_webhook.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

data "aws_iam_policy_document" "sns_topic_policy" {
  policy_id = "__default_policy_ID"

  statement {
    actions = [
      "SNS:Subscribe"
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalOrgID"

      values = [
        data.aws_organizations_organization.owner.id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = [
      aws_sns_topic.github_app_noq_webhook.arn,
    ]

    sid = "Allow-other-account-to-subscribe-to-topic"
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# This is to optionally manage the CloudWatch Log Group for the Lambda Function.
# If skipping this resource configuration, also add "logs:CreateLogGroup" to the IAM policy below.
resource "aws_cloudwatch_log_group" "github_app_noq_webhook" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
}

resource "aws_iam_role" "github_app_noq_webhook_lambda" {
  name               = "github_app_noq_webhook_lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  inline_policy {
    name = "sns_publish"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action   = ["sns:Publish"]
          Effect   = "Allow"
          Resource = aws_sns_topic.github_app_noq_webhook.arn
        },
      ]
    })
  }

  inline_policy {
    name = "lambda_logs"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
          ]
          Effect   = "Allow"
          Resource = ["arn:aws:logs:*:*:*"]
        },
      ]
    })
  }
}

data "archive_file" "lambda_zip_file_int" {
  type        = "zip"
  output_path = "/tmp/lambda_zip_file_int.zip"
  source {
    content  = file("../../serverless/github-app-webhook-lambda/github-app-webhook-lambda.py")
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "github_app_webhook" {
  filename         = data.archive_file.lambda_zip_file_int.output_path
  source_code_hash = data.archive_file.lambda_zip_file_int.output_base64sha256
  function_name    = var.lambda_function_name
  role             = aws_iam_role.github_app_noq_webhook_lambda.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"

  environment {
    variables = {
      topic_arn = aws_sns_topic.github_app_noq_webhook.arn
    }
  }

  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_function_url" "github_app_webhook" {
  function_name      = aws_lambda_function.github_app_webhook.function_name
  authorization_type = "NONE"
}