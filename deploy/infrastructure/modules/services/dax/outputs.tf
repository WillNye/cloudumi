output "dax_cluster_arn" {
  description = "The ARN of the DAX cluster"
  value       = aws_dax_cluster.dax_cluster.arn
}

output "dax_cluster_address" {
  description = "The DNS name of the DAX cluster without the port appended"
  value       = aws_dax_cluster.dax_cluster.cluster_address
}

output "dax_configuration_endpoint" {
  description = "The configuration endpoint for this DAX cluster, consisting of a DNS name and a port number"
  value       = aws_dax_cluster.dax_cluster.configuration_endpoint
}

