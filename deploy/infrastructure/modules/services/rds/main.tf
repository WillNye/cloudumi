resource "aws_db_subnet_group" "noq_rds_subnet_group" {
  name       = "rds_${var.cluster_id}_subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "noq_rds_sg" {
  name        = "${var.cluster_id}_rds_access_sg"
  description = "Allows access to the ${var.cluster_id} RDS cluster, internally to AWS."
  vpc_id      = var.vpc_id

  ingress {
    description = "Access to the port the RDS cluster is listening on."
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.private_subnet_cidr_blocks
  }

  egress {
    description = "Full egress access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-vpc-no-public-egress-sgr
  }

  tags = merge(
    var.tags,
    {
      Name = "allow_access_to_noq"
    }
  )
}

resource "aws_iam_role" "rds_monitoring_role" {

  name = "${var.cluster_id}-rds-monitoring"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      },
    ]
  })

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"]
}

resource "aws_rds_cluster" "postgresql" {
  cluster_identifier        = var.cluster_id
  engine                    = "aurora-postgresql"
  db_subnet_group_name      = aws_db_subnet_group.noq_rds_subnet_group.name
  vpc_security_group_ids    = [aws_security_group.noq_rds_sg.id]
  availability_zones        = ["${var.region}a", "${var.region}b"]
  database_name             = var.database_name
  master_username           = var.master_username
  master_password           = var.master_password
  backup_retention_period   = 5
  preferred_backup_window   = "07:00-09:00"
  final_snapshot_identifier = "${var.cluster_id}-final-snapshot"
  kms_key_id                = var.kms_key_id
  storage_encrypted         = true
  deletion_protection       = true
  tags                      = var.tags
  lifecycle {
    ignore_changes = [
      availability_zones,
    ]
  }
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count                           = var.rds_instance_count
  identifier_prefix               = replace("${var.cluster_id}-", "_", "-")
  cluster_identifier              = aws_rds_cluster.postgresql.id
  instance_class                  = var.rds_instance_type
  engine                          = aws_rds_cluster.postgresql.engine
  engine_version                  = aws_rds_cluster.postgresql.engine_version
  performance_insights_kms_key_id = var.kms_key_id
  performance_insights_enabled    = true
  monitoring_role_arn             = aws_iam_role.rds_monitoring_role.arn
  monitoring_interval             = 30
  lifecycle {
    ignore_changes = [
      cluster_identifier,
    ]
  }
}

