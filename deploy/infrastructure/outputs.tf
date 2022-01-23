output "attributes" {
  description = "The attributes configured (for automation)"
  value = var.attributes
}

output "ecs_awslogs_group" {
  description = "The ecs aws logs group name (for automation)"
  value = module.tenant_container_service.ecs_awslogs_group
}

output "ecs_security_group" {
  description = "The ECS security group ID"
  value = module.tenant_container_service.ecs_security_group_id
}

output "ecs_task_execution_role_arn" {
  description = "The ECS task execution role ARN to be configured"
  value = module.tenant_container_service.ecs_task_execution_role
}

output "ecs_task_role_arn" {
  description = "The ECS task role ARN to be configured"
  value = module.tenant_container_service.ecs_task_role
}

output "namespace" {
  description = "The configured namespace (for automation)"
  value = var.namespace
}

output "redis_primary_cluster_address" {
  description = "The address of the primary redis cluster endpoint"
  value       = module.tenant_elasticache_service.redis_primary_cluster_address
}

output "region" {
  description = "The region configured (for automation)"
  value       = var.region
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

output "stage" {
  description = "The configured stage (for automation)"
  value = var.stage
}

output "subnet_name_az0" {
  description = "The configured subnet name for AZ0 (for automation)"
  value = module.tenant_networking.vpc_subnet_public_id[0]
}

output "subnet_name_az1" {
  description = "The configured subnet name for AZ1 (for automation)"
  value = module.tenant_networking.vpc_subnet_public_id[1]
}

output "target_group_arn" {
  description = "The target group ARN, needs to be updated in the BUILD file under the ecs-cli call"
  value = module.tenant_networking.target_group_arn
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