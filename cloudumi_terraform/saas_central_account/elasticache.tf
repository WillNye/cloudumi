// module "redis-cluster" {
//     source                      = "clouddrove/elasticache/aws"
//     version                     = "0.15.0"
//     name                        = "cloudumi-cluster-es-2"
//     environment                 = "staging"
//     label_order                 = ["environment","name"]
//     cluster_replication_enabled = true
//     engine                      = "redis"
//     engine_version              = "6.x"
//     family                      = "redis6.x"
//     port                        = 6379
//     node_type                   = "cache.t3.micro"
//     subnet_ids                  = ["subnet-0661531a5841a1af7"]
//     // security_group_ids          = [module.redis-sg.security_group_ids]
//     availability_zones          = ["us-west-2a","us-west-2b" ]
//     auto_minor_version_upgrade  = true
//     replicas_per_node_group     = 0
//     num_node_groups             = 1
//     automatic_failover_enabled  = false
//   }


resource "aws_elasticache_cluster" "cloudumi-customer-cache" {
  cluster_id           = "cloudumi-es"
  replication_group_id = aws_elasticache_replication_group.cloudumi-customer-cache.id
}

resource "aws_elasticache_replication_group" "cloudumi-customer-cache" {
  replication_group_id          = "cloudumi-redis-cluster"
  replication_group_description = "Cloudumi Redis Cluster Replication Group"
  node_type                     = "cache.t3.micro"
  transit_encryption_enabled    = false
  at_rest_encryption_enabled    = true
  port                          = 6379
  parameter_group_name          = "default.redis6.x.cluster.on"
  automatic_failover_enabled    = true

  cluster_mode {
    replicas_per_node_group = 0
    num_node_groups         = 1
  }
  snapshot_retention_limit = 1
}