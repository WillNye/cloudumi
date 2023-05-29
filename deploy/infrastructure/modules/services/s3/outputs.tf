output "cloudumi_bucket_name" {
  description = "CloudUmi bucket for configuration, logs, etc"
  value       = aws_s3_bucket.cloudumi_files_bucket.bucket
}

output "cloudumi_temp_files_bucket_name" {
  description = "CloudUmi bucket for temporary files"
  value       = aws_s3_bucket.cloudumi_temp_files_bucket.bucket
}

output "tenant_configuration_bucket_name" {
  description = "Bucket for storing configuration files"
  value       = aws_s3_bucket.tenant_configuration_store.bucket
}