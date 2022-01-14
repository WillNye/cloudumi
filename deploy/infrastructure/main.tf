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
  stage = var.stage
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
  container_insights = var.container_insights
  capacity_providers = var.capacity_providers
}

module "tenant_dynamodb_service" {
  source = "./modules/services/dynamo"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
}

module "tenant_elasticache_service" {
  source = "./modules/services/elasticache"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
  redis_node_type = var.redis_node_type
}

module "tenant_s3_service" {
  source = "./modules/services/s3"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
}

module "tenant_networking" {
  source = "./modules/services/networking"
  namespace = var.namespace
  stage = var.stage
  delimiter = var.delimiter
  convert_case = var.convert_case
  default_tags = var.default_tags
  vpc_cidr = var.vpc_cidr
  subnet_azs = var.subnet_azs
  public_subnet_cidrs = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  system_bucket = module.tenant_s3_service.cloudumi_bucket_name
  domain_name = var.domain_name
  attributes = var.attributes
  main = var.name
}