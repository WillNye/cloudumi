terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.74"
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

module "tenant_s3_service" {
  source               = "./modules/services/s3"
  tags                 = var.tags
  bucket_name_prefix   = "noq-global-${var.stage}"
  s3_access_log_bucket = var.s3_access_log_bucket
}

module "tenant_dynamodb_service" {
  source                       = "./modules/services/dynamo"
  dynamo_table_replica_regions = var.dynamo_table_replica_regions
  tags                         = var.tags
}

module "github_app_integration" {
  source = "./modules/services/github-app-integration"
  tags   = var.tags
}
