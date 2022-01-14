output "cloudumi_bucket_name" {
  description = "CloudUmi bucket for configuration, logs, etc"
  value = module.aws_s3_bucket.cloudumi_files_bucket.bucket
}