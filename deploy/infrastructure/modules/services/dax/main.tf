resource "aws_iam_role" "dax_role" {
  name = "${var.stage}-${var.tenant_name}-daxRole"
  lifecycle {
    ignore_changes = all
  }

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "dax.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
  inline_policy {
    name = "dynamo_access_policy"
    policy = jsonencode({
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "dynamodb:DescribeTable",
            "dynamodb:PutItem",
            "dynamodb:GetItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan",
            "dynamodb:BatchGetItem",
            "dynamodb:BatchWriteItem",
            "dynamodb:ConditionCheckItem"
          ],
          "Resource" : [
            "arn:aws:dynamodb:*:*:table/*"
          ]
        }
      ],
      "Version" : "2012-10-17"
    })
  }
}

resource "aws_dax_parameter_group" "dax_param_group" {
  name = "${var.stage}-${var.tenant_name}-pg"

  parameters {
    name  = "query-ttl-min"
    value = "10"
  }

  parameters {
    name  = "record-ttl-hour"
    value = "4"
  }
}

resource "aws_dax_subnet_group" "dax_subnet_group" {
  name       = "${var.stage}-${var.tenant_name}-sg"
  subnet_ids = var.subnet_ids
}

#tfsec:ignore:*
resource "aws_dax_cluster" "dax_cluster" {
  cluster_name         = "${var.stage}-${var.tenant_name}"
  iam_role_arn         = aws_iam_role.dax_role.arn
  node_type            = var.node_type
  replication_factor   = var.node_count
  parameter_group_name = aws_dax_parameter_group.dax_param_group.name
  security_group_ids   = var.security_group_ids
  subnet_group_name    = aws_dax_subnet_group.dax_subnet_group.name
  server_side_encryption = {
    enabled = true
  }
}

