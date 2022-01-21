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

  force_destroy = true

  tags = merge(
    var.tags,
    {}
  )
}