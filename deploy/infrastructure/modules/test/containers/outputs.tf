output "container" {
    description = "In the aws execute-command, this is the --container argument"
    value = "${var.ecs_cluster_name}-api"
}

output "region" {
    description = "In the aws execute-command this is the --region argument"
    value = var.region
}

output "task" {
    description = "In the aws execute-command, this is the --task argument"
    value = aws_ecs_service.test_service.id
}