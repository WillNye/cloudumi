output "rds_port" {
  value = aws_rds_cluster.postgresql.port
}

output "rds_endpoint" {
  value = aws_rds_cluster.postgresql.endpoint
}

output "default_database" {
  value = var.database_name
}