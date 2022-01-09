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
