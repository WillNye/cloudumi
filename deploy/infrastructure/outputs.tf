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

output "vpc_arn" {
  description = "The ARN of the VPC configured"
  value = module.tenant_networking.vpc_arn
}

output "vpc_cidr_range" {
  description = "The CIDR range of the VPC"
  value = module.tenant_networking.vpc_cidr_range
}

output "vpc_subnet_public_cidr" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value = module.tenant_networking.vpc_subnet_public_cidr
}

output "vpc_subnet_private_cidr" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value = module.tenant_networking.vpc_subnet_private_cidr
}

output "vpc_subnet_public_id" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value = module.tenant_networking.vpc_subnet_public_id
}

output "vpc_subnet_private_id" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value = module.tenant_networking.vpc_subnet_private_id
}