terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
  backend "s3" {
    bucket         = "noq-terraform-state"
    key            = "terraform/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "noq_terraform_state"
  }

}

provider "aws" {
  profile = var.tf_profile
  region  = var.region
}

module "tenant_container_service" {
  source = "./modules/services/containers"

  allowed_inbound_cidr_blocks = var.allowed_inbound_cidr_blocks
  attributes = var.attributes
  capacity_providers = var.capacity_providers
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
  container_insights = var.container_insights
  lb_port = var.lb_port
  noq_core = var.noq_core
  stage = var.stage
  tags = var.tags
  timeout = var.timeout
  vpc_id = module.tenant_networking.vpc_id
}

module "tenant_dynamodb_service" {
  source = "./modules/services/dynamo"

  attributes = var.attributes
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
  dynamo_table_replica_regions = var.dynamo_table_replica_regions
  noq_core = var.noq_core
  tags = var.tags
  timeout = var.timeout
}

module "tenant_elasticache_service" {
  source = "./modules/services/elasticache"

  attributes = var.attributes
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
  redis_node_type = var.redis_node_type
  subnet_ids = module.tenant_networking.vpc_subnet_private_id
  tags = var.tags
  timeout = var.timeout
  vpc_id = module.tenant_networking.vpc_id
}

module "tenant_s3_service" {
  source = "./modules/services/s3"

  attributes = var.attributes
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
  tags = var.tags
  timeout = var.timeout
}

module "tenant_networking" {
  source = "./modules/services/networking"

  allowed_inbound_cidr_blocks = var.allowed_inbound_cidr_blocks
  attributes = var.attributes
  cluster_id = "${replace(var.zone, ".", "-")}-${var.namespace}-${var.stage}-${var.attributes}"
  convert_case = var.convert_case
  delimiter = var.delimiter
  domain_name = var.domain_name
  lb_port = var.lb_port
  namespace = var.namespace
  stage = var.stage
  subnet_azs = var.subnet_azs
  system_bucket = module.tenant_s3_service.cloudumi_bucket_name
  tags = var.tags
  timeout = var.timeout
  zone = var.zone
}