output "cloudumi_central_role_arns" {
  description = "ID of the cloudumi central role arns"
  value       = aws_dynamodb_table.cloudumi_central_role_arns.id
}

output "cloudumi_identity_groups_multitenant_id" {
  description = "ID of the cloudumi identity groups multitenant table"
  value       = aws_dynamodb_table.cloudumi_identity_groups_multitenant.id
}

output "cloudumi_cloudtrail_multitenant_id" {
  description = "ID of cloudtrail multitenant"
  value       = aws_dynamodb_table.cloudumi_cloudtrail_multitenant.id
}

output "cloudumi_config_multitenant_id" {
  description = "ID of config multitenant"
  value       = aws_dynamodb_table.cloudumi_config_multitenant.id
}

output "cloudumi_identity_requests_multitenant_id" {
  description = "ID of cloudumi identity requests multitenant"
  value       = aws_dynamodb_table.cloudumi_identity_requests_multitenant.id
}

output "cloudumi_policy_requests_multitenant_id" {
  description = "ID of cloudumi policy requests multitenant"
  value       = aws_dynamodb_table.cloudumi_policy_requests_multitenant.id
}

output "cloudumi_notifications_multitenant_id" {
  description = "ID of cloudumi notification multitenant"
  value       = aws_dynamodb_table.cloudumi_notifications_multitenant.id
}

output "cloudumi_users_multitenant_id" {
  description = "ID of cloudumi users multitenant"
  value       = aws_dynamodb_table.cloudumi_users_multitenant.id
}

output "cloudumi_tenant_static_configs_id" {
  description = "ID of cloudumi tenant static configs"
  value       = aws_dynamodb_table.cloudumi_tenant_static_configs.id
}

output "cloudumi_identity_users_multitenant_id" {
  description = "ID of cloudumi identity users multitenant"
  value       = aws_dynamodb_table.cloudumi_identity_users_multitenant.id
}

output "noq_api_keys_id" {
  description = "ID of noq api keys"
  value       = aws_dynamodb_table.noq_api_keys.id
}

output "cloudumi_iamroles_multitenant_id" {
  description = "ID of cloudumi amroles multitenant"
  value       = aws_dynamodb_table.cloudumi_iamroles_multitenant.id
}

output "noq_aws_accounts_id" {
  description = "ID of noq aws accounts"
  value       = aws_dynamodb_table.noq_aws_accounts.id
}
