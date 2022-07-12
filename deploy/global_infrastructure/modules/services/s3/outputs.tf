output "noq_legal_docs_bucket_name" {
  description = "Bucket for storing legal documentation"
  value       = aws_s3_bucket.noq_legal_docs.bucket
}