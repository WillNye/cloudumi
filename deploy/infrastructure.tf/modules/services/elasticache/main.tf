#####
# VPC and subnets
#####
data "aws_vpc" "default" {
  default = true
}

data "aws_subnet_ids" "all" {
  vpc_id = data.aws_vpc.default.id
}

#####
# Elasticache Redis
#####
module "redis" {
  source  = "umotif-public/elasticache-redis/aws"
  version = "2.2.0"

  name_prefix           = "noq-sharded"
  number_cache_clusters = 2
  node_type             = "cache.t3.small"

  cluster_mode_enabled    = true
  replicas_per_node_group = 1
  num_node_groups         = 1

  engine_version           = "6.x"
  port                     = 6379
  maintenance_window       = "mon:03:00-mon:04:00"
  snapshot_window          = "04:00-06:00"
  snapshot_retention_limit = 7

  automatic_failover_enabled = true

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = "1234567890asdfghjkl"

  apply_immediately = true
  family            = "redis6.x"
  description       = "Test elasticache redis."

  subnet_ids         = data.aws_subnet_ids.all.ids
  vpc_id             = data.aws_vpc.default.id
  security_group_ids = []

  ingress_cidr_blocks = []

  parameter = [
    {
      name  = "repl-backlog-size"
      value = "16384"
    }
  ]

  tags = {
    Project = "Test"
  }
}


####

# Legacy

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


// resource "aws_elasticache_cluster" "cloudumi-customer-cache" {
//   cluster_id           = "cloudumi-es"
//   replication_group_id = aws_elasticache_replication_group.cloudumi-customer-cache.id
// }

// resource "aws_elasticache_replication_group" "cloudumi-customer-cache" {
//   replication_group_id          = "cloudumi-redis-cluster"
//   replication_group_description = "Cloudumi Redis Cluster Replication Group"
//   node_type                     = "cache.t3.micro"
//   transit_encryption_enabled    = false
//   at_rest_encryption_enabled    = true
//   port                          = 6379
//   parameter_group_name          = "default.redis6.x.cluster.on"
//   automatic_failover_enabled    = true

//   cluster_mode {
//     replicas_per_node_group = 0
//     num_node_groups         = 1
//   }
//   snapshot_retention_limit = 1
// }