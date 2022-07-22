output "tenant_details_table_name" {
  description = "Name of the table containing tenant details like eula agreement and membership tier"
  value       = aws_dynamodb_table.tenant_details.name
}
