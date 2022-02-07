output "attributes" {
  description = "The attributes configured (for automation)"
  value       = var.attributes
}

output "bucket_name" {
  description = "The bucket used for cloudumi operation"
  value       = module.tenant_s3_service.cloudumi_bucket_name
}

output "cluster_id" {
  description = "The configured cluster id (for automation)"
  value       = local.cluster_id
}

output "domain_name" {
  description = "The configured domain name, which is derived from {namespace}.{zone}"
  value       = "${var.namespace}.${var.zone}"
}

output "ecs_awslogs_group" {
  description = "The ecs aws logs group name (for automation)"
  value       = module.tenant_container_service.ecs_awslogs_group
}

output "ecs_cluster_name" {
  description = "The ECS cluster name"
  value       = module.tenant_container_service.ecs_cluster_name
}

output "ecs_security_group" {
  description = "The ECS security group ID"
  value       = module.tenant_container_service.ecs_security_group_id
}

output "ecs_task_execution_role_arn" {
  description = "The ECS task execution role ARN to be configured, note this has been referenced as ecsTaskExecutionRole in previous configurations"
  value       = module.tenant_container_service.ecs_task_execution_role
}

output "ecs_task_role_arn" {
  description = "The ECS task role ARN to be configured; note this has been referenced as NoqClusterRole1 in previous configurations"
  value       = module.tenant_container_service.ecs_task_role
}

# output "elasticache_parameter_group_id" {
#   description = "The ElastiCache parameter group name."
#   value       = module.tenant_elasticache_service.elasticache_parameter_group_id
# }

# output "elasticache_primary_cluster_address" {
#   description = "The address of the primary redis cluster endpoint"
#   value       = module.tenant_elasticache_service.elasticache_primary_cluster_address
# }

# output "elasticache_replication_group_reader_address" {
#   description = "The address of the endpoint for the reader node in the replication group."
#   value       = module.tenant_elasticache_service.elasticache_replication_group_reader_address
# }

output "elasticache_nodes" {
  description = "List of node objects including id, address, port and availability_zone"
  value       = module.tenant_elasticache_service.elasticache_nodes
}

output "namespace" {
  description = "The configured namespace (for automation)"
  value       = var.namespace
}

output "private_subnets" {
  description = "All private subnets used"
  value       = module.tenant_networking.vpc_subnet_private_id
}

output "profile" {
  description = "The selected profile"
  value       = var.profile
}

output "sentry_dsn" {
  description = "The configured sentry dsn (for exception tracking)"
  value       = var.sentry_dsn
}

output "region" {
  description = "The region configured (for automation)"
  value       = var.region
}

output "registry_repository_url_api" {
  description = "The respository URL for the API registry"
  value       = module.tenant_container_service.registry_repository_url_api[0].repository_url
}

output "registry_repository_url_celery" {
  description = "The respository URL for the Celery registry"
  value       = module.tenant_container_service.registry_repository_url_celery[0].repository_url
}

output "registry_repository_url_frontend" {
  description = "The respository URL for the Frontend registry"
  value       = module.tenant_container_service.registry_repository_url_frontend[0].repository_url
}

output "sns_registration_topic_arn" {
  description = "The SNS registration topic ARN that is used to trigger customer registration using the NOQ CF templates" 
  value = module.tenant_messaging.sns_registration_topic_arn
}

output "sns_registration_topic_name" {
  description = "The SNS topic name that is used to trigger customer registration using the NOQ CF template"
  value = module.tenant_messaging.sns_registration_topic_name
}

output "sqs_registration_queue_arn" {
  description = "The SQS registration queue ARN that is used to trigger customer registration using the NOQ CF templates" 
  value = module.tenant_messaging.sqs_registration_queue_arn
}

output "sqs_registration_queue_name" {
  description = "The SQS queue name that is used to trigger customer registration using the NOQ CF template"
  value = module.tenant_messaging.sqs_registration_queue_name
}

output "sqs_registration_response_queue_arn" {
  description = "The SQS registration response queue ARN that is used to trigger customer registration using the NOQ CF templates" 
  value = module.tenant_messaging.sqs_registration_response_queue_arn
}

output "sqs_registration_response_queue_name" {
  description = "The SQS response queue name that is used to trigger customer registration using the NOQ CF template"
  value = module.tenant_messaging.sqs_registration_response_queue_name
}
output "stage" {
  description = "The configured stage (for automation)"
  value       = var.stage
}

output "subnet_name_private_az0" {
  description = "The configured subnet name for AZ0 (for automation)"
  value       = module.tenant_networking.vpc_subnet_private_id[0]
}

output "subnet_name_private_az1" {
  description = "The configured subnet name for AZ1 (for automation)"
  value       = module.tenant_networking.vpc_subnet_private_id[1]
}

output "subnet_name_public_az0" {
  description = "The configured subnet name for AZ0 (for automation)"
  value       = module.tenant_networking.vpc_subnet_public_id[0]
}

output "subnet_name_public_az1" {
  description = "The configured subnet name for AZ1 (for automation)"
  value       = module.tenant_networking.vpc_subnet_public_id[1]
}

output "target_group_arn" {
  description = "The target group ARN, needs to be updated in the BUILD file under the ecs-cli call"
  value       = module.tenant_networking.target_group_arn
}

output "tenant_configuration_bucket_name" {
  description = "The tenant configuration bucket name to store NOQ configuration"
  value       = module.tenant_s3_service.tenant_configuration_bucket_name
}

output "vpc_arn" {
  description = "The ARN of the VPC configured"
  value       = module.tenant_networking.vpc_arn
}

output "vpc_cidr_range" {
  description = "The CIDR range of the VPC"
  value       = module.tenant_networking.vpc_cidr_range
}

output "vpc_subnet_public_cidr" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value       = module.tenant_networking.vpc_subnet_public_cidr
}

output "vpc_subnet_private_cidr" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value       = module.tenant_networking.vpc_subnet_private_cidr
}

output "vpc_subnet_public_id" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value       = module.tenant_networking.vpc_subnet_public_id
}

output "vpc_subnet_private_id" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value       = module.tenant_networking.vpc_subnet_private_id
}

output "zone" {
  description = "The configured zone (for automation)"
  value       = var.zone
}

output "celery_log_level" {
  description = "The configured celery log level"
  value       = var.celery_log_level
}

output "celery_concurrency" {
  description = "The configured celery concurrency"
  value       = var.celery_concurrency
}