

# Creating Amazon EFS File system
resource "aws_efs_file_system" "data_storage" {
  # Creating the AWS EFS lifecycle policy
  # Amazon EFS supports two lifecycle policies. Transition into IA and Transition out of IA
  # Transition into IA transition files into the file systems's Infrequent Access storage class
  # Transition files out of IA storage
  lifecycle_policy {
    transition_to_ia = "AFTER_7_DAYS"
  }
  kms_key_id = var.kms_key_id
  encrypted  = true
  tags       = var.tags
}

# Creating the EFS access point for AWS EFS File system
resource "aws_efs_access_point" "data_storage_access_point" {
  file_system_id = aws_efs_file_system.data_storage.id
  tags           = var.tags
}
# Creating the AWS EFS System policy to transition files into and out of the file system.
resource "aws_efs_file_system_policy" "policy" {
  file_system_id                     = aws_efs_file_system.data_storage.id
  bypass_policy_lockout_safety_check = true
  # The EFS System Policy allows clients to mount, read and perform
  # write operations on File system
  # The communication of client and EFS is set using aws:secureTransport Option
  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Id": "Policy01",
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": {
                "AWS": "*"
            },
            "Action": "*",
            "Resource": "${aws_efs_file_system.data_storage.arn}",
            "Condition": {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        },
        {
            "Sid": "Statement",
            "Effect": "Allow",
            "Principal": {
                "AWS": "${var.ecs_task_role_arn}"
            },
            "Resource": "${aws_efs_file_system.data_storage.arn}",
            "Action": [
                "elasticfilesystem:ClientMount",
                "elasticfilesystem:ClientRootAccess",
                "elasticfilesystem:ClientWrite"
            ]
        }
    ]
}
POLICY
}
# Creating the AWS EFS Mount point in a specified Subnet
# AWS EFS Mount point uses File system ID to launch.
resource "aws_efs_mount_target" "efs-mount-target" {
  file_system_id  = aws_efs_file_system.data_storage.id
  subnet_id       = var.subnet_ids[0]
  security_groups = [aws_security_group.efs-sg.id]
}

resource "aws_efs_mount_target" "efs-mount-target-2" {
  file_system_id  = aws_efs_file_system.data_storage.id
  subnet_id       = var.subnet_ids[1]
  security_groups = [aws_security_group.efs-sg.id]
}

resource "aws_security_group" "efs-sg" {
  name        = "${var.cluster_id}-efs-access-sg"
  description = "Allows access to EFS storage from the containers"
  vpc_id      = var.vpc_id

  ingress {
    description     = "NFS for container access to EFS storage"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = var.ecs_security_group_id
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
      Name = "allow_access_to_efs"
    }
  )
}