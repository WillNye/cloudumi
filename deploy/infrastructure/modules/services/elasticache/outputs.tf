# output "elasticache_parameter_group_id" {
#   description = "The ElastiCache parameter group name."
#   value       = module.redis.elasticache_parameter_group_id
# }

# output "elasticache_primary_cluster_address" {
#   description = "The address of the primary redis cluster endpoint"
#   value       = module.redis.elasticache_replication_group_primary_endpoint_address
# }

# output "elasticache_replication_group_reader_address" {
#   description = "The address of the endpoint for the reader node in the replication group."
#   value       = module.redis.elasticache_replication_group_reader_endpoint_address
# }

output "elasticache_nodes" {
  description = "List of node objects including id, address, port and availability_zone"
  value       = aws_elasticache_cluster.redis.cache_nodes
}

output "elasticache_redis_primary_endpoint_address" {
  description = "Address of the endpoint for the primary node in the replication group, if the cluster mode is disabled."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "elasticache_redis_primary_endpoint_port" {
  description = "Port of the endpoint for the primary node in the replication group, if the cluster mode is disabled."
  value       = aws_elasticache_replication_group.redis.port
}