data "aws_elb_service_account" "main" {}

resource "aws_s3_bucket_public_access_block" "noq_legal_docs" {
  bucket = aws_s3_bucket.noq_legal_docs.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

resource "aws_s3_bucket" "noq_legal_docs" {
  bucket = "${var.bucket_name_prefix}-legal-docs"
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
          "arn:aws:s3:::${var.bucket_name_prefix}-legal-docs/*",
          "arn:aws:s3:::${var.bucket_name_prefix}-legal-docs"
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