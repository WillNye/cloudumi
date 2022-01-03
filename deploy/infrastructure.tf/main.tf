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
  cluster_stage = "${var.stage}"
}

module "tenant_elasticache_service" {
  source = "./modules/services/elasticache"
  cluster_stage = "${var.stage}"
}

module "tenant_s3_service" {
  source = "./modules/services/s3"
  bucket_name_prefix = "${var.bucket_name_prefix}"
  cluster_id = "${var.cluster_id}"
  cluster_Stage = "${var.cluster_stage}"
}