output "redis_primary_cluster_address" {
  description = "The address of the primary redis cluster endpoint"
  value       = module.tenant_elasticache_service.redis_primary_cluster_address

}