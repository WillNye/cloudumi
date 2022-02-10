data "aws_elb_service_account" "main" {}

resource "aws_s3_bucket_public_access_block" "cloudumi_files_bucket" {
  bucket = aws_s3_bucket.cloudumi_files_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket" "cloudumi_files_bucket" {
  bucket = "${lower(var.bucket_name_prefix)}.${var.cluster_id}"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }

  policy = <<POLICY
  {
    "Id": "Policy",
    "Version": "2012-10-17",
    "Statement":
    [
      {
        "Action": [
          "s3:PutObject"
        ],
        "Effect": "Allow",
        "Resource": [
          "arn:aws:s3:::${lower(var.bucket_name_prefix)}.${var.cluster_id}/AWSLogs/*"
        ],
        "Principal": {
          "AWS": [
            "${data.aws_elb_service_account.main.arn}"
          ]
        }
      }
    ]
  }
  POLICY

  force_destroy = true

  tags = merge(
    var.tags,
    {}
  )

  logging {
    target_bucket = var.s3_access_log_bucket
  }
}

resource "aws_s3_bucket_public_access_block" "tenant_configuration_store" {
  bucket = aws_s3_bucket.tenant_configuration_store.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket" "tenant_configuration_store" {
  bucket = "${var.cluster_id}-tenant-configuration-store"
  acl    = "private"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }

  policy = <<POLICY
  {
    "Id": "Policy",
    "Version": "2012-10-17",
    "Statement":
    [
      {
        "Action": [
          "s3:ListBucket",
          "s3:GetObject"
        ],
        "Effect": "Allow",
        "Resource": [
          "arn:aws:s3:::${var.cluster_id}-tenant-configuration-store/*",
          "arn:aws:s3:::${var.cluster_id}-tenant-configuration-store"
        ],
        "Principal": {
          "AWS": [
            "arn:aws:iam::940552945933:root"
          ]
        }
      }
    ]
  }
  POLICY

  force_destroy = true

  tags = merge(
    var.tags,
    {}
  )

  logging {
    target_bucket = var.s3_access_log_bucket
  }
}