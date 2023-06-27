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
  name               = "SNSFailureFeedback"
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
resource "aws_cloudwatch_log_group" "example" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
}

# See also the following AWS managed policy: AWSLambdaBasicExecutionRole
data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_policy" "lambda_logging" {
  name        = "lambda_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy      = data.aws_iam_policy_document.lambda_logging.json
}

resource "aws_iam_role" "github_app_noq_webhook_lambda" {
  name               = "github_app_noq_webhook_lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  inline_policy {
    name = "my_inline_policy"

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
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.github_app_noq_webhook_lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
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