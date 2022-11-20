output "aws_efs_data_storage_access_point_id" {
  description = "The ID of the EFS access point"
  value       = aws_efs_access_point.data_storage_access_point.id
}

output "aws_efs_data_storage_file_system_id" {
  description = "The ID of the EFS file system"
  value       = aws_efs_file_system.data_storage.id
}