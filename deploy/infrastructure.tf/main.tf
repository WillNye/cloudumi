terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  profile = "default"
  region  = "${var.region}"
}

module "tenant_dynamodb_service" {
  source = "./modules/services/dynamo"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
}

module "tenant_elasticache_service" {
  source = "./modules/services/elasticache"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
}

module "tenant_s3_service" {
  source = "./modules/services/s3"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
}