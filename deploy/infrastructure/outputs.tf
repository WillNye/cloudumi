output "redis_primary_cluster_address" {
  description = "The address of the primary redis cluster endpoint"
  value       = module.tenant_elasticache_service.redis_primary_cluster_address
}

output "registry_repository_url_api" {
  description = "The respository URL for the API registry"
  value       = module.tenant_container_service.registry_repository_url_api
}

output "registry_repository_url_celery" {
  description = "The respository URL for the Celery registry"
  value       = module.tenant_container_service.registry_repository_url_celery
}

output "registry_repository_url_frontend" {
  description = "The respository URL for the Frontend registry"
  value       = module.tenant_container_service.registry_repository_url_frontend
}