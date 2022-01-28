module "redis" {
  source  = "umotif-public/elasticache-redis/aws"
  version = "2.2.0"

  name_prefix           = var.cluster_id
  number_cache_clusters = 2
  node_type             = var.redis_node_type

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

  subnet_ids         = var.subnet_ids
  vpc_id             = var.vpc_id
  security_group_ids = [aws_security_group.redis-sg.id]

  ingress_cidr_blocks = []

  parameter = [
    {
      name  = "repl-backlog-size"
      value = "16384"
    }
  ]

  tags = merge(
    var.tags,
    {
      "Project": "Test"
    }
  )
}

resource "aws_security_group" "redis-sg" {
  name        = "${var.cluster_id}-redis-access-sg"
  description = "Allows access to Redis services, internally to AWS."
  vpc_id      = var.vpc_id

  ingress {
    description = "Access from other security groups to the Redis cluster access port"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    security_groups = var.redis_cluster_access_sg_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "allow_access_to_noq"
    }
  )
}