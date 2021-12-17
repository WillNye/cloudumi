resource "aws_cloudwatch_log_group" "noq_log_group" {
  name = format("%s-%s-%s", var.namespace, var.stage, var.cluster_id)
}

resource "aws_ecs_cluster" "noq" {
  name               = format("%s-%s-%s", var.namespace, var.stage, var.cluster_id)
  capacity_providers = var.capacity_providers
  configuration {
    execute_command_configuration {
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