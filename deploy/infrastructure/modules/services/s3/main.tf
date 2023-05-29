data "aws_elb_service_account" "main" {}

resource "aws_s3_bucket_public_access_block" "cloudumi_log_bucket" {
  bucket = aws_s3_bucket.cloudumi_log_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

#tfsec:ignore:aws-s3-enable-bucket-logging
resource "aws_s3_bucket" "cloudumi_log_bucket" {
  bucket = "cloudumi-log-${var.cluster_id}"
  acl    = "private"

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
          "arn:aws:s3:::cloudumi-log-${var.cluster_id}/*",
          "arn:aws:s3:::cloudumi-log-${var.cluster_id}"
        ],
        "Principal": {
          "AWS": [
            "arn:aws:iam::${var.account_id}:root"
          ]
        }
      }
    ]
  }
  POLICY

  versioning {
    enabled = true
  }

  lifecycle_rule {
    enabled = true

    expiration {
      days = var.log_expiry
    }
  }

  tags = var.tags
}

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
    target_bucket = aws_s3_bucket.cloudumi_log_bucket.id
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
            "arn:aws:iam::${var.account_id}:root"
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
    target_bucket = aws_s3_bucket.cloudumi_log_bucket.id
  }
}

# Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "tenant_configuration_store_sse" {
  bucket = aws_s3_bucket.tenant_configuration_store.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.bucket_encryption_key
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudumi_log_bucket_sse" {
  bucket = aws_s3_bucket.cloudumi_log_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.bucket_encryption_key
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudumi_files_bucket_sse" {
  bucket = aws_s3_bucket.cloudumi_files_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.bucket_encryption_key
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudumi_temp_files_bucket" {
  bucket = aws_s3_bucket.cloudumi_temp_files_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  restrict_public_buckets = true
  ignore_public_acls      = true
}

#tfsec:ignore:aws-s3-enable-versioning
resource "aws_s3_bucket" "cloudumi_temp_files_bucket" {
  bucket = "cloudumi-temp-files-${var.cluster_id}"
  acl    = "private"

  policy = <<POLICY
  {
    "Id": "Policy",
    "Version": "2012-10-17",
    "Statement":
    [
      {
        "Action": [
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetObject",
          "s3:DeleteObject"
        ],
        "Effect": "Allow",
        "Resource": [
          "arn:aws:s3:::cloudumi-temp-files-${var.cluster_id}",
          "arn:aws:s3:::cloudumi-temp-files-${var.cluster_id}/*"
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

  lifecycle_rule {
    id      = "tmpfilesexpiry"
    enabled = true

    expiration {
      days = 90
    }
  }

  logging {
    target_bucket = aws_s3_bucket.cloudumi_log_bucket.id
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudumi_temp_files_bucket_sse" {
  bucket = aws_s3_bucket.cloudumi_temp_files_bucket.bucket

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.bucket_encryption_key
      sse_algorithm     = "aws:kms"
    }
  }
}