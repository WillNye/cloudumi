resource "aws_iam_role" "ecs_task_role" {
  count       = var.modify_ecs_task_role ? 1 : 0
  name        = "${var.cluster_id}-ecsTaskRole"
  description = "Referenced previously as NoqClusterRole1; the role is used by the ECS containers running NOQ logic"
  lifecycle {
    ignore_changes = all
  }
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
  tags = var.noq_core ? { "noq-authorized" : lower("${var.cluster_id}-ecsTaskRole@noq.dev") } : {}
  inline_policy {
    name = "ecs_task_role_policy"
    policy = jsonencode({
      "Statement" : [
        {
          "Action" : [
            "kms:Decrypt",
            "kms:DescribeKey",
            "kms:Encrypt",
            "kms:GenerateDataKey",
            "kms:GenerateDataKeyWithoutPlaintext",
            "kms:ReEncryptFrom",
            "kms:ReEncryptTo"
          ],
          "Effect" : "Allow",
          "Resource" : "${var.bucket_encryption_key}"
        },
        {
          "Action" : [
            "secretsmanager:describesecret",
            "secretsmanager:GetSecretValue",
            "secretsmanager:ListSecretVersionIds",
            "secretsmanager:ListSecrets",
          ],
          "Effect" : "Allow",
          "Resource" : "${var.aws_secrets_manager_arn}"
        },
        {
          "Action" : [
            "access-analyzer:*",
            "cloudtrail:*",
            "cloudwatch:*",
            "config:SelectResourceConfig",
            "config:SelectAggregateResourceConfig",
            "dax:batchgetitem",
            "dax:batchwriteitem",
            "dax:deleteitem",
            "dax:describe*",
            "dax:getitem",
            "dax:putitem",
            "dax:query",
            "dax:scan",
            "dax:updateitem",
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
            "s3:GetObject",
            "s3:GetBucketLocation",
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
          "Sid" : "GitHubAppIntegration",
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
        }
      ],
      "Version" : "2012-10-17"
    })
  }
}

data "aws_iam_role" "ecs_task_role_pre_existing" {
  count = var.modify_ecs_task_role ? 0 : 1
  name  = "${var.cluster_id}-ecsTaskRole"
}