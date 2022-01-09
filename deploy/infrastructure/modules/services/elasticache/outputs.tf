output "redis_primary_cluster_address" {
  description = "The address of the primary redis cluster endpoint"
  value       = module.redis.elasticache_replication_group_primary_endpoint_address
}