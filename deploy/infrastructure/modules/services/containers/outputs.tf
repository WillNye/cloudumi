output "ecs_awslogs_group" {
  description = "The ECS AWS Logs Group Name"
  value       = aws_cloudwatch_log_group.noq_log_group.name
}

output "ecs_security_group_id" {
  description = "The configured ecs security group for access (for automation)"
  value       = aws_security_group.ecs-sg.id
}

output "ecs_task_execution_role" {
  description = "The ecsTaskExecutionRole ARN to be configured"
  value       = aws_iam_role.ecs_task_execution_role.arn
} 

output "ecs_task_role" {
  description = "The ecsTaskRole ARN to be configured"
  value       = aws_iam_role.ecs_task_role.arn
}

output "registry_repository_url_api" {
  description = "The respository URL for the API registry"
  value       = aws_ecr_repository.noq_ecr_repository-api
}

output "registry_repository_url_celery" {
  description = "The respository URL for the Celery registry"
  value       = aws_ecr_repository.noq_ecr_repository-celery
}

output "registry_repository_url_frontend" {
  description = "The respository URL for the Frontend registry"
  value       = aws_ecr_repository.noq_ecr_repository-frontend
}
