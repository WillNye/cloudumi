resource "aws_flow_log" "flow_log_binding" {
  iam_role_arn    = aws_iam_role.flow_log_role.arn
  log_destination = aws_cloudwatch_log_group.flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main_vpc.id
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  name = "flow_logs"
}

resource "aws_iam_role" "flow_log_role" {
  name = "flow_log_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "vpc-flow-logs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "flow_log_role_policy" {
  name = "flow_log_role_policy"
  role = aws_iam_role.flow_log_role.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_vpc" "main_vpc" {
  cidr_block           = "10.${var.attributes}.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  instance_tenancy     = "default"

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_internet_gateway" "main_igw" {
  vpc_id = aws_vpc.main_vpc.id

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_subnet" "subnet_public_az0" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = "10.${var.attributes}.254.0/24"
  map_public_ip_on_launch = "false"
  availability_zone       = element(var.subnet_azs, 0)

  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}

resource "aws_subnet" "subnet_public_az1" {
  vpc_id                  = aws_vpc.main_vpc.id
  cidr_block              = "10.${var.attributes}.255.0/24"
  map_public_ip_on_launch = "false"
  availability_zone       = element(var.subnet_azs, 1)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}


resource "aws_subnet" "subnet_private_az0" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.${var.attributes}.0.0/18"
  availability_zone = element(var.subnet_azs, 0)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}

resource "aws_subnet" "subnet_private_az1" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.${var.attributes}.64.0/18"
  availability_zone = element(var.subnet_azs, 1)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}