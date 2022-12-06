output "bucket_encryption_kms_key" {
  description = "KMS key used to encrypt bucket objects"
  value       = aws_kms_key.s3_bucket_encryption_key.arn
}

output "cloudumi_bucket_name" {
  description = "CloudUmi bucket for configuration, logs, etc"
  value       = aws_s3_bucket.cloudumi_files_bucket.bucket
}

output "tenant_configuration_bucket_name" {
  description = "Bucket for storing configuration files"
  value       = aws_s3_bucket.tenant_configuration_store.bucket
}