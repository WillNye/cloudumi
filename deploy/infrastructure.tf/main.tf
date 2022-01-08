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
  profile = "default"
  region  = var.region
}

module "tenant_container_service" {
  source = "./modules/services/containers"
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
}

module "tenant_s3_service" {
  source = "./modules/services/s3"
  cluster_id = "${var.namespace}-${var.name}-${var.stage}-${var.attributes}"
  noq_core = var.noq_core
}