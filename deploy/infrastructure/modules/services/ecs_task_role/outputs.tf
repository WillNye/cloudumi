output "ecs_task_role" {
  description = "The ecsTaskRole ARN to be configured"
  value       = length(aws_iam_role.ecs_task_role) > 0 ? one(aws_iam_role.ecs_task_role).arn : null
}
