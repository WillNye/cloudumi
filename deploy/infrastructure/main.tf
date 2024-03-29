terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.6.2"
    }
  }

  required_version = ">= 1.1.5"
  backend "s3" {
    bucket         = "noq-terraform-state"
    key            = "terraform/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "noq_terraform_state"
    # All of the profiles are stored in S3 on the dev account
    profile = "staging/staging_admin"
  }

}

provider "aws" {
  profile = var.profile
  region  = var.region
}

provider "aws" {
  alias   = "aws_east"
  profile = var.profile
  region  = "us-east-1"
}

locals {
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
}

module "tenant_networking" {
  source = "./modules/services/networking"

  allowed_inbound_cidr_blocks = var.allowed_inbound_cidr_blocks
  attributes                  = var.attributes
  cluster_id                  = local.cluster_id
  convert_case                = var.convert_case
  delimiter                   = var.delimiter
  domain_name                 = var.domain_name
  load_balancer_internal      = var.load_balancer_internal
  lb_port                     = var.lb_port
  namespace                   = var.namespace
  stage                       = var.stage
  subnet_azs                  = var.subnet_azs
  system_bucket               = module.tenant_s3_service.cloudumi_bucket_name
  lb_bucket                   = module.tenant_s3_service.cloudumi_lb_bucket_name
  tags                        = var.tags
  timeout                     = var.timeout
  zone                        = var.zone
}

module "tenant_s3_service" {
  source = "./modules/services/s3"

  account_id            = var.account_id
  attributes            = var.attributes
  cluster_id            = local.cluster_id
  log_expiry            = var.log_expiry
  noq_core              = var.noq_core
  tags                  = var.tags
  timeout               = var.timeout
  bucket_encryption_key = module.tenant_container_service.kms_key_id
}

module "tenant_messaging" {
  source = "./modules/services/messaging"

  account_id                    = var.account_id
  cluster_id                    = local.cluster_id
  tags                          = var.tags
  global_tenant_data_account_id = var.global_tenant_data_account_id
  region                        = var.region
}

module "tenant_messaging_us-east-1" {
  source = "./modules/services/messaging-us-east-1"

  account_id                                 = var.account_id
  cluster_id                                 = local.cluster_id
  tags                                       = var.tags
  aws_marketplace_subscription_sns_topic_arn = var.aws_marketplace_subscription_sns_topic_arn
  providers = {
    aws = aws.aws_east
  }
}

module "tenant_dynamodb_service" {
  source = "./modules/services/dynamo"

  attributes                   = var.attributes
  cluster_id                   = local.cluster_id
  dynamo_table_replica_regions = var.dynamo_table_replica_regions
  noq_core                     = var.noq_core
  tags                         = var.tags
  timeout                      = var.timeout
}

module "tenant_dax_cluster" {
  source = "./modules/services/dax"

  namespace          = var.namespace
  stage              = var.stage
  subnet_ids         = module.tenant_networking.vpc_subnet_private_id
  security_group_ids = [module.tenant_networking.vpc_to_dax_sg_id]
  node_type          = var.dax_node_type
  node_count         = var.dax_node_count
}

module "tenant_elasticache_service" {
  source = "./modules/services/elasticache"

  attributes                  = var.attributes
  cluster_id                  = local.cluster_id
  noq_core                    = var.noq_core
  private_subnet_cidr_blocks  = module.tenant_networking.vpc_subnet_private_cidr
  redis_cluster_access_sg_ids = [module.tenant_container_service.ecs_security_group_id]
  redis_node_type             = var.redis_node_type
  redis_secrets               = var.redis_secrets
  subnet_ids                  = module.tenant_networking.vpc_subnet_private_id
  tags                        = var.tags
  timeout                     = var.timeout
  vpc_id                      = module.tenant_networking.vpc_id
  elasticache_node_type       = var.elasticache_node_type
}

module "tenant_ses_service" {
  source = "./modules/services/ses"

  notifications_mail_from_domain = var.notifications_mail_from_domain
  notifications_sender_identity  = var.notifications_sender_identity
  tags                           = var.tags
}

module "tenant_ecs_task_role" {
  source = "./modules/services/ecs_task_role"

  cloudumi_files_bucket                  = module.tenant_s3_service.cloudumi_bucket_name
  cluster_id                             = local.cluster_id
  modify_ecs_task_role                   = var.modify_ecs_task_role
  registration_queue_arn                 = module.tenant_messaging.sqs_registration_queue_arn
  github_app_noq_webhook_queue_arn       = module.tenant_messaging.sqs_github_app_noq_webhook_queue_arn
  aws_marketplace_subscription_queue_arn = module.tenant_messaging_us-east-1.aws_marketplace_subscription_queue_arn
  tenant_configuration_bucket_name       = module.tenant_s3_service.tenant_configuration_bucket_name
  aws_secrets_manager_arn                = module.tenant_container_service.aws_secrets_manager_arn
  noq_core                               = var.noq_core
  bucket_encryption_key                  = module.tenant_container_service.kms_key_id
}

module "tenant_container_service" {
  source = "./modules/services/containers"

  allowed_inbound_cidr_blocks            = var.allowed_inbound_cidr_blocks
  attributes                             = var.attributes
  capacity_providers                     = var.capacity_providers
  cloudumi_files_bucket                  = module.tenant_s3_service.cloudumi_bucket_name
  cloudumi_temp_files_bucket             = module.tenant_s3_service.cloudumi_temp_files_bucket_name
  cluster_id                             = local.cluster_id
  container_insights                     = var.container_insights
  lb_port                                = var.lb_port
  load_balancer_sgs                      = [module.tenant_networking.load_balancer_security_group]
  namespace                              = var.namespace
  noq_core                               = var.noq_core
  region                                 = var.region
  registration_queue_arn                 = module.tenant_messaging.sqs_registration_queue_arn
  github_app_noq_webhook_queue_arn       = module.tenant_messaging.sqs_github_app_noq_webhook_queue_arn
  aws_marketplace_subscription_queue_arn = module.tenant_messaging_us-east-1.aws_marketplace_subscription_queue_arn
  stage                                  = var.stage
  subnet_ids                             = module.tenant_networking.vpc_subnet_private_id
  tags                                   = var.tags
  tenant_configuration_bucket_name       = module.tenant_s3_service.tenant_configuration_bucket_name
  timeout                                = var.timeout
  vpc_cidr_range                         = module.tenant_networking.vpc_cidr_range
  vpc_id                                 = module.tenant_networking.vpc_id
  aws_secrets_manager_cluster_string     = var.aws_secrets_manager_cluster_string
  bucket_encryption_key                  = module.tenant_container_service.kms_key_id
}

module "tenant_storage" {
  source                = "./modules/services/storage"
  attributes            = var.attributes
  ecs_security_group_id = [module.tenant_container_service.ecs_security_group_id]
  kms_key_id            = module.tenant_container_service.kms_key_id
  cluster_id            = local.cluster_id
  region                = var.region
  tags                  = var.tags
  vpc_id                = module.tenant_networking.vpc_id
  subnet_ids            = module.tenant_networking.vpc_subnet_private_id
  ecs_task_role_arn     = module.tenant_container_service.ecs_task_role
}

module "noq_db_cluster" {
  source                     = "./modules/services/rds"
  cluster_id                 = local.cluster_id
  database_name              = var.noq_db_database_name
  rds_instance_count         = var.noq_db_instance_count
  rds_instance_type          = var.noq_db_instance_type
  region                     = var.region
  tags                       = var.tags
  vpc_id                     = module.tenant_networking.vpc_id
  subnet_ids                 = module.tenant_networking.vpc_subnet_private_id
  private_subnet_cidr_blocks = module.tenant_networking.vpc_subnet_private_cidr
  master_username            = var.noq_db_username
  master_password            = var.noq_db_password
  kms_key_id                 = module.tenant_container_service.kms_key_id
}
