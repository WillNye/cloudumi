output "account_id" {
  description = "The account id in which this infrastructre is built in"
  value       = var.account_id
}

output "attributes" {
  description = "The attributes configured (for automation)"
  value       = var.attributes
}

output "global_tenant_data_account_id" {
  description = "Account ID of the AWS Tenant Data Account"
  value       = var.global_tenant_data_account_id
}

output "global_tenant_data_role_name" {
  description = "Role name of the AWS Tenant Data Account"
  value       = var.global_tenant_data_role_name
}

output "legal_docs_bucket_name" {
  description = "The S3 bucket containing templates for our legal documentation"
  value       = var.legal_docs_bucket_name
}

output "bucket_name" {
  description = "The bucket used for cloudumi operation"
  value       = module.tenant_s3_service.cloudumi_bucket_name
}

output "temp_files_bucket_name" {
  description = "The bucket used for temporary files (unit/functional test results)"
  value       = module.tenant_s3_service.cloudumi_temp_files_bucket_name
}

output "cluster_id" {
  description = "The configured cluster id (for automation)"
  value       = local.cluster_id
}

output "domain_name" {
  description = "The configured domain name"
  value       = var.domain_name
}

output "landing_page_domains" {
  description = "The domain names that should be used for common endpoints, like tenant_registration. This should NOT be set for non-noq (self-hosted) deployments"
  value       = var.landing_page_domains
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
  value       = module.tenant_ecs_task_role.ecs_task_role
}

output "worker_count" {
  description = "Desired number of celery workers"
  value       = var.worker_count
}

output "api_count" {
  description = "Desired number of api containers"
  value       = var.api_count
}

output "elasticache_nodes" {
  description = "List of node objects including id, address, port and availability_zone"
  value       = module.tenant_elasticache_service.elasticache_nodes
}

output "elasticache_redis_primary_endpoint_address" {
  description = "Address of the endpoint for the primary node in the replication group, if the cluster mode is disabled."
  value       = module.tenant_elasticache_service.elasticache_redis_primary_endpoint_address
}

output "elasticache_redis_primary_endpoint_port" {
  description = "Port of the endpoint for the primary node in the replication group, if the cluster mode is disabled."
  value       = module.tenant_elasticache_service.elasticache_redis_primary_endpoint_port
}

output "notifications_sender_identity" {
  description = "ARN of the notifications sender identity"
  value       = module.tenant_ses_service.notifications_sender_identity
}

output "namespace" {
  description = "The configured namespace (for automation)"
  value       = var.namespace
}

output "private_subnets" {
  description = "All private subnets used"
  value       = module.tenant_networking.vpc_subnet_private_id
}

output "aws_efs_data_storage_access_point_id" {
  description = "The ID of the EFS access point"
  value       = module.tenant_storage.aws_efs_data_storage_access_point_id
}

output "aws_efs_data_storage_file_system_id" {
  description = "The ID of the EFS file system"
  value       = module.tenant_storage.aws_efs_data_storage_file_system_id
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
  value       = length(module.tenant_container_service.registry_repository_url_api) > 0 ? module.tenant_container_service.registry_repository_url_api[0].repository_url : ""
}

output "sns_registration_topic_arn" {
  description = "The SNS registration topic ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = module.tenant_messaging.sns_registration_topic_arn
}

output "sns_registration_topic_name" {
  description = "The SNS topic name that is used to trigger customer registration using the NOQ CF template"
  value       = module.tenant_messaging.sns_registration_topic_name
}

output "sqs_registration_queue_arn" {
  description = "The SQS registration queue ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = module.tenant_messaging.sqs_registration_queue_arn
}

output "sqs_registration_queue_name" {
  description = "The SQS queue name that is used to trigger customer registration using the NOQ CF template"
  value       = module.tenant_messaging.sqs_registration_queue_name
}

output "sqs_registration_response_queue_arn" {
  description = "The SQS registration response queue ARN that is used to trigger customer registration using the NOQ CF templates"
  value       = module.tenant_messaging.sqs_registration_response_queue_arn
}

output "sqs_registration_response_queue_name" {
  description = "The SQS response queue name that is used to trigger customer registration using the NOQ CF template"
  value       = module.tenant_messaging.sqs_registration_response_queue_name
}

output "sqs_github_app_webhook_queue_arn" {
  description = "The SQS to see GitHub App Noq Webhook Events"
  value       = module.tenant_messaging.sqs_github_app_webhook_queue_arn
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

output "kms_key_id" {
  description = "The configured KMS key ID"
  value       = module.tenant_container_service.kms_key_id
}

output "google_analytics_tracking_id" {
  description = "The configured Google Analytics tracking ID"
  value       = var.google_analytics_tracking_id
}

output "aws_secrets_manager_arn" {
  description = "The configured AWS Secrets Manager ARN"
  value       = module.tenant_container_service.aws_secrets_manager_arn
}

output "dax_cluster_arn" {
  description = "The ARN of the DAX cluster"
  value       = module.tenant_dax_cluster.dax_cluster_arn
}

output "dax_cluster_address" {
  description = "The DNS name of the DAX cluster without the port appended"
  value       = module.tenant_dax_cluster.dax_cluster_address
}

output "dax_configuration_endpoint" {
  description = "The configuration endpoint for this DAX cluster, consisting of a DNS name and a port number"
  value       = module.tenant_dax_cluster.dax_configuration_endpoint
}

output "noq_db_endpoint" {
  description = "The endpoint of the noq db cluster"
  value       = module.noq_db_cluster.rds_endpoint
}

output "noq_db_port" {
  description = "The port number of the noq db cluster"
  value       = module.noq_db_cluster.rds_port
}

output "noq_db_database_name" {
  description = "The default database of the noq db cluster"
  value       = module.noq_db_cluster.default_database
}

