resource "aws_cloudwatch_log_group" "noq_log_group" {
  name = var.cluster_id
}

resource "aws_kms_key" "noq_ecs_kms_key" {
  description             = "ECS KMS key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
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
  inline_policy {
    name = "ecs_task_role_policy"
    policy = jsonencode({
      "Statement" : [
        {
          "Action" : [
            "access-analyzer:*",
            "cloudtrail:*",
            "cloudwatch:*",
            "config:SelectResourceConfig",
            "config:SelectAggregateResourceConfig",
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
            "config:BatchGet*",
            "config:List*",
            "config:Select*",
            "ec2:DescribeSubnets",
            "ec2:describevpcendpoints",
            "ec2:DescribeVpcs",
            "iam:GetAccountAuthorizationDetails",
            "iam:ListAccountAliases",
            "iam:ListAttachedRolePolicies",
            "ec2:describeregions",
            "s3:GetBucketPolicy",
            "s3:GetBucketTagging",
            "s3:ListAllMyBuckets",
            "s3:ListBucket",
            "s3:PutBucketPolicy",
            "s3:PutBucketTagging",
            "sns:GetTopicAttributes",
            "sns:ListTagsForResource",
            "sns:ListTopics",
            "sns:SetTopicAttributes",
            "sns:TagResource",
            "sns:UnTagResource",
            "sqs:GetQueueAttributes",
            "sqs:GetQueueUrl",
            "sqs:ListQueues",
            "sqs:ListQueueTags",
            "sqs:SetQueueAttributes",
            "sqs:TagQueue",
            "sqs:UntagQueue"
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
          "Effect" : "Allow",
          "Action" : [
            "s3:ListStorageLensConfigurations",
            "s3:ListAccessPointsForObjectLambda",
            "s3:GetAccessPoint",
            "s3:GetAccountPublicAccessBlock",
            "s3:ListAllMyBuckets",
            "s3:ListAccessPoints",
            "s3:ListJobs",
            "s3:ListMultiRegionAccessPoints"
          ],
          "Resource" : "*"
        },
        {
          "Effect" : "Allow",
          "Action" : [
            "s3:get*",
            "s3:list*"
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