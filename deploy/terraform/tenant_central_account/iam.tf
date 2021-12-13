terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_iam_role" "ConsoleMeSpokeRole" {
  path                 = "/"
  name                 = "ConsoleMeSpokeRole"
  assume_role_policy   = data.aws_iam_policy_document.consoleme_target_trust_policy.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "consoleme_target_trust_policy" {
  statement {
    sid = "ConsoleMeAssumesTarget"
    actions = [
    "sts:AssumeRole"]
    effect = "Allow"
    principals {
      identifiers = [
      aws_iam_role.ConsoleMeCentralRole.arn]
      type = "AWS"
    }
  }
}

data "aws_iam_policy_document" "consoleme_central_trust_policy" {
  statement {
    sid = "ConsoleMeAssumesTarget"
    actions = [
    "sts:AssumeRole"]
    effect = "Allow"
    principals {
      identifiers = [
      "arn:aws:iam::259868150464:role/NoqClusterRole1"]
      type = "AWS"
    }
  }
}

resource "aws_iam_role" "ConsoleMeCentralRole" {
  path                 = "/"
  name                 = "ConsoleMeCentralRole"
  assume_role_policy   = data.aws_iam_policy_document.consoleme_central_trust_policy.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy" "IAMPolicy" {
  policy = <<EOF
{
    "Statement": [
        {
            "Action": [
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
            "Effect": "Allow",
            "Resource": [
                "*"
            ]
        },
        {
            "Action": [
                "ses:sendemail",
                "ses:sendrawemail"
            ],
            "Condition": {
                "StringLike": {
                    "ses:FromAddress": [
                        "email_address_here@example.com"
                    ]
                }
            },
            "Effect": "Allow",
            "Resource": "arn:aws:ses:*:123456789:identity/your_identity.example.com"
        },
        {
            "Action": [
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
            "Effect": "Allow",
            "Resource": "*"
        }
    ],
    "Version": "2012-10-17"
}
EOF
  role   = aws_iam_role.ConsoleMeCentralRole.name
}

resource "aws_iam_role_policy" "IAMPolicy2" {
  policy = <<EOF
{
    "Statement": [
        {
            "Action": [
                "autoscaling:Describe*",
                "cloudwatch:Get*",
                "cloudwatch:List*",
                "config:BatchGet*",
                "config:List*",
                "config:Select*",
                "ec2:describeregions",
                "ec2:DescribeSubnets",
                "ec2:describevpcendpoints",
                "ec2:DescribeVpcs",
                "iam:*",
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
                "sqs:UntagQueue",
                "organizations:ListAccounts"
            ],
            "Effect": "Allow",
            "Resource": [
                "*"
            ],
            "Sid": "iam"
        }
    ],
    "Version": "2012-10-17"
}
EOF
  role   = aws_iam_role.ConsoleMeSpokeRole.name
}
