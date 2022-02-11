locals {
  function_name = "handleNoqRegistrationResponseToCF"
  source_path   = "${path.module}/${local.function_name}"
  output_path   = "${path.module}/${local.function_name}/dist"
  zip_path      = "${path.module}/${local.function_name}/dist/lambda.zip"
}

resource "aws_iam_role" "lambda_exec_role" {
  name               = "lambda_exec_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      }
    }
  ]
}
EOF
}

data "aws_iam_policy_document" "lambda_policy_doc" {
  # General lambda execution role stuff
  statement {
    sid    = "AllowInvokingLambdas"
    effect = "Allow"

    resources = [
      "arn:aws:lambda:*:*:function:*"
    ]

    actions = [
      "lambda:InvokeFunction"
    ]
  }

  statement {
    sid    = "AllowCreatingLogGroups"
    effect = "Allow"

    resources = [
      "arn:aws:logs:*:*:*"
    ]

    actions = [
      "logs:CreateLogGroup"
    ]
  }

  statement {
    sid    = "AllowWritingLogs"
    effect = "Allow"

    resources = [
      "arn:aws:logs:*:*:log-group:/aws/lambda/*:*"
    ]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  # Add specific policy statements
  statement {
    sid    = "AllowSQSReceiveMessage"
    effect = "Allow"

    resources = [
      var.registration_response_queue
    ]

    actions = [
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage"
    ]
  }
}

resource "aws_iam_policy" "lambda_iam_policy" {
  name   = "lambda_iam_policy"
  policy = data.aws_iam_policy_document.lambda_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  policy_arn = aws_iam_policy.lambda_iam_policy.arn
  role       = aws_iam_role.lambda_exec_role.name
}

resource "null_resource" "install_python_dependencies" {
  provisioner "local-exec" {
    command = "bash ${path.module}/scripts/create_pkg.sh"

    environment = {
      source_path   = local.source_path
      output_path   = local.output_path
      function_name = local.function_name
      path_module   = path.module
      runtime       = var.runtime
      path_cwd      = path.cwd
    }
  }

  triggers = {
    zip     = "${fileexists(local.zip_path)}"
    handler = "${filemd5("${local.source_path}/handler.py")}"
  }
}

data "archive_file" "create_dist_pkg" {
  depends_on  = [null_resource.install_python_dependencies]
  source_dir  = local.output_path
  output_path = local.zip_path
  type        = "zip"
}

resource "aws_lambda_function" "handle_noq_registration_response" {
  function_name = local.function_name
  description   = "Process registration responses"
  handler       = "handler.emit_s3_response"
  runtime       = var.runtime

  environment {
    variables = {
      PHYSICAL_RESOURCE_ID = "f4b52b3d-0056-4ec0-aca4-ac61ed2efd1d"
      REGION               = var.region
      ACCOUNT_ID           = var.account_id
      CLUSTER_ID           = var.cluster_id
    }
  }

  role        = aws_iam_role.lambda_exec_role.arn
  memory_size = 128
  timeout     = 300

  depends_on       = [null_resource.install_python_dependencies]
  source_code_hash = data.archive_file.create_dist_pkg.output_base64sha256
  filename         = data.archive_file.create_dist_pkg.output_path

  tracing_config {
    mode = "Active"
  }
}

resource "aws_lambda_event_source_mapping" "handle_noq_registration_response_event_handler" {
  event_source_arn = var.registration_response_queue
  function_name    = aws_lambda_function.handle_noq_registration_response.arn
}