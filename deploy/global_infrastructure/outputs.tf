output "global_account_id" {
  description = "The account id in which this infrastructre is built in"
  value       = var.account_id
}

output "legal_docs_bucket_name" {
  description = "The bucket used to store legal documents"
  value       = module.tenant_s3_service.noq_legal_docs_bucket_name
}

output "tenant_details_info_table_name" {
  description = "Name of the table containing tenant details like eula agreement and membership tier"
  value       = module.tenant_dynamodb_service.tenant_details_table_name
}

output "github_app_webhook_sns_topic_arn" {
  description = "ARN of the topic receiving GitHub App events"
  value       = module.github_app_integration.github_app_webhook_sns_topic_arn
}

output "global_profile" {
  description = "The selected profile"
  value       = var.profile
}

output "global_region" {
  description = "The region configured (for automation)"
  value       = var.region
}

output "stage" {
  description = "The configured stage (for automation)"
  value       = var.stage
}