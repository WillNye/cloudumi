output "ecs_cluster_id" {
  description = "ID of the ECS Cluster"
  value       = concat(aws_ecs_cluster.noq.*.id, [""])[0]
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS Cluster"
  value       = concat(aws_ecs_cluster.noq.*.arn, [""])[0]
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.noq.name
}

output "vpc_id" {
  description = "The id of the VPC"
  value       = data.aws_vpc.default.id
}

output "subnets" {
  description = "The subnets of the VPC"
  value       = data.aws_subnet_ids.all.ids
}

output "elasticache_replication_group_member_clusters" {
  description = "Redis Node Clusters"
  value       = module.redis.elasticache_replication_group_member_clusters
}

output "elasticache_replication_group_primary_endpoint_address" {
  description = "Redis Node Clusters"
  value       = module.redis.elasticache_replication_group_primary_endpoint_address
}

output "elasticache_replication_group_reader_endpoint_address" {
  description = "Redis Node Clusters"
  value       = module.redis.elasticache_replication_group_reader_endpoint_address
}