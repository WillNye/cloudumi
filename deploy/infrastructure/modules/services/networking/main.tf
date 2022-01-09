resource "aws_cloudwatch_log_group" "noq_log_group" {
  name = "${var.cluster_id}"
}

resource "aws_kms_key" "noq_ecs_kms_key" {
  description             = "ECS KMS key"
  deletion_window_in_days = 7
}

resource "aws_ecs_cluster" "noq_ecs_cluster" {
  name               = "${var.cluster_id}"
  capacity_providers = var.capacity_providers
  configuration {
    execute_command_configuration {
      kms_key_id = aws_kms_key.noq_ecs_kms_key.arn
      logging = "OVERRIDE"

      log_configuration {
        cloud_watch_encryption_enabled = true
        cloud_watch_log_group_name     = aws_cloudwatch_log_group.noq_log_group.name
      }
    }
  }
  setting {
    name  = "containerInsights"
    value = var.container_insights ? "enabled" : "disabled"
  }
}

resource "aws_ecr_repository" "noq_ecr_repository-api" {
  name                 = "${var.stage}-registry-api"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0  

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "noq_ecr_repository-celery" {
  name                 = "${var.stage}-registry-celery"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0  

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "noq_ecr_repository-frontend" {
  name                 = "${var.stage}-registry-frontend"
  image_tag_mutability = "MUTABLE"
  count                = var.noq_core ? 1 : 0  

  image_scanning_configuration {
    scan_on_push = true
  }
}