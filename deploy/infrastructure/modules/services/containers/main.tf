data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "aws_region" "current" {}

resource "aws_cloudwatch_log_group" "noq_log_group" {
  name              = var.cluster_id
  retention_in_days = 365
  kms_key_id        = aws_kms_key.noq_ecs_kms_key.arn
}

resource "aws_kms_key" "noq_ecs_kms_key" {
  description             = "ECS KMS key"
  policy                  = data.aws_iam_policy_document.cloudwatch.json
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "cloudwatch" {
  name          = format("alias/%s-%s", var.cluster_id, "kms")
  target_key_id = aws_kms_key.noq_ecs_kms_key.key_id
}

resource "aws_ecs_cluster" "noq_ecs_cluster" {
  name               = var.cluster_id
  capacity_providers = var.capacity_providers
  configuration {
    execute_command_configuration {
      kms_key_id = aws_kms_key.noq_ecs_kms_key.arn
      logging    = "OVERRIDE"

      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.noq_log_group.name
      }
    }
  }

  setting {
    name  = "containerInsights"
    value = var.container_insights ? "enabled" : "disabled"
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_ecr_repository" "noq_ecr_repository-api" {
  name                 = "${var.namespace}-${var.stage}-registry-api"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_ecr_repository" "noq_ecr_repository-celery" {
  name                 = "${var.namespace}-${var.stage}-registry-celery"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_secretsmanager_secret" "noq_secrets" {
  name       = "${var.namespace}-${var.stage}-noq_secrets"
  kms_key_id = aws_kms_key.noq_ecs_kms_key.key_id
}

resource "aws_secretsmanager_secret_version" "noq_secrets" {
  secret_id = aws_secretsmanager_secret.noq_secrets.id
}

resource "aws_ecr_repository" "noq_ecr_repository-frontend" {
  name                 = "${var.namespace}-${var.stage}-registry-frontend"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name        = "${var.cluster_id}-ecsTaskExecutionRole"
  description = "This is also known as the ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })
  inline_policy {
    name = "ecs_task_execution_role_policy"
    policy = jsonencode({
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          "Resource" : "*"
        },
        {
          "Effect" : "Allow",
          "Action" : [
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel",
            "kms:Decrypt",
            "logs:DescribeLogGroups",
            "logs:CreateLogStream",
            "logs:DescribeLogStreams",
            "logs:PutLogEvents",
          ],
          "Resource" : "*"
        }
      ]
    })
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_iam_role" "ecs_task_role" {
  name        = "${var.cluster_id}-ecsTaskRole"
  description = "Referenced previously as NoqClusterRole1; the role is used by the ECS containers running NOQ logic"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })
  tags = { "noq-authorized" : lower("${var.cluster_id}-ecsTaskRole@noq.dev") }
  inline_policy {
    name = "ecs_task_role_policy"
    policy = jsonencode({
      "Statement" : [
        {
          "Action" : [
            "secretsmanager:describesecret",
            "secretsmanager:GetSecretValue",
            "secretsmanager:listsecrets",
            "secretsmanager:listsecretversionids"
          ],
          "Effect" : "Allow",
          "Resource" : [
            "${aws_secretsmanager_secret.noq_secrets.arn}"
          ]
        },
        {
          "Action" : [
            "access-analyzer:ValidatePolicy",
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel",
            "cloudwatch:*",
            "cognito-idp:*",
            "dynamodb:batchgetitem",
            "dynamodb:batchwriteitem",
            "dynamodb:deleteitem",
            "dynamodb:describe*",
            "dynamodb:getitem",
            "dynamodb:getrecords",
            "dynamodb:getsharditerator",
            "dynamodb:putitem",
            "dynamodb:query",
            "dynamodb:scan",
            "dynamodb:updateitem",
            "dynamodb:CreateTable",
            "dynamodb:UpdateTimeToLive",
            "sns:createplatformapplication",
            "sns:createplatformendpoint",
            "sns:deleteendpoint",
            "sns:deleteplatformapplication",
            "sns:getendpointattributes",
            "sns:getplatformapplicationattributes",
            "sns:listendpointsbyplatformapplication",
            "sns:publish",
            "sns:setendpointattributes",
            "sns:setplatformapplicationattributes",
            "sts:assumerole"
          ],
          "Effect" : "Allow",
          "Resource" : [
            "*"
          ]
        },
        {
          "Action" : [
            "autoscaling:Describe*",
            "cloudwatch:Get*",
            "cloudwatch:List*",
            "s3:GetBucketPolicy",
            "s3:GetBucketTagging",
            "s3:ListBucket",
            "sns:GetTopicAttributes",
            "sns:ListTagsForResource",
            "sns:ListTopics",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
            "sqs:ListQueues",
            "sqs:ListQueueTags",
          ],
          "Effect" : "Allow",
          "Resource" : "*"
        },
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : [
            "s3:ListBucket",
            "s3:GetObject"
          ],
          "Resource" : [
            "arn:aws:s3:::${var.tenant_configuration_bucket_name}",
            "arn:aws:s3:::${var.tenant_configuration_bucket_name}/*"
          ]
        },
        {
          "Action" : [
            "s3:ListBucket",
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject"
          ],
          "Effect" : "Allow",
          "Resource" : [
            "arn:aws:s3:::${var.cloudumi_files_bucket}",
            "arn:aws:s3:::${var.cloudumi_files_bucket}/*"
          ]
        },
        {
          "Action" : [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueUrl",
            "sqs:GetQueueAttributes",
          ],
          "Effect" : "Allow",
          "Resource" : [
            "${var.registration_queue_arn}",
          ]
        },
        {
          "Effect" : "Allow",
          "Action" : [
            "kms:Decrypt",
            "logs:DescribeLogGroups",
            "logs:CreateLogStream",
            "logs:DescribeLogStreams",
            "logs:PutLogEvents",
          ],
          "Resource" : "*"
        }
      ],
      "Version" : "2012-10-17"
    })
  }
}

resource "aws_security_group" "ecs-sg" {
  name        = "${var.cluster_id}-ecs-access-sg"
  description = "Allows access to ECS services, internally to AWS."
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP for accessing Noq from the load balancer"
    from_port       = 8092
    to_port         = 8092
    protocol        = "tcp"
    security_groups = var.load_balancer_sgs
  }

  ingress {
    description     = "SSH for accessing Noq for debugging"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [var.test_access_sg_id]
  }

  ingress {
    description = "SSH access to API container"
    from_port   = 2222
    to_port     = 2222
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_range]
  }

  ingress {
    description = "SSH access to Celery container"
    from_port   = 2223
    to_port     = 2223
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr_range]
  }

  egress {
    description = "Full egress access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-vpc-no-public-egress-sgr
  }

  tags = merge(
    var.tags,
    {
      Name = "allow_access_to_noq"
    }
  )
}

data "aws_iam_policy_document" "cloudwatch" {
  policy_id = "key-policy-cloudwatch"
  statement {
    sid = "Enable IAM User Permissions"
    actions = [
      "kms:*",
    ]
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = [
        format(
          "arn:%s:iam::%s:root",
          data.aws_partition.current.partition,
          data.aws_caller_identity.current.account_id
        )
      ]
    }
    resources = ["*"]
  }
  statement {
    sid = "AllowCloudWatchLogs"
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*"
    ]
    effect = "Allow"
    principals {
      type = "Service"
      identifiers = [
        format(
          "logs.%s.amazonaws.com",
          data.aws_region.current.name
        )
      ]
    }
    resources = ["*"]
  }
}