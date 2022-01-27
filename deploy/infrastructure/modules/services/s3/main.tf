data "aws_elb_service_account" "main" {}

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
}