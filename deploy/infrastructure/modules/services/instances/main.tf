data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_security_group" "jumpbox_sg" {
  name        = "${var.cluster_id}-ec2-jumpbox-sg"
  description = "Allows access to the EC2 jumpbox VM."
  vpc_id      = var.vpc_id

  ingress {
    description = "Access to jumpbox"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_inbound_cidr_blocks
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
      Name = "jumpbox-access-sg"
    }
  )
}

resource "aws_key_pair" "noq_key" {
  key_name   = "${var.cluster_id}_noq_key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCgmXD4cJXjJEdJo0xLqJVRtB6K5Aw84G2MMXdlKVcoDrBsRRAvYZkJ7fuNJYFe5eEKnoctu6THH86TBdqnA+EOqynmvqCGRDc/xdhPcyP1jBxPXM0EWaXWSipYJUhtIXEevBlrWQDHC2LV2iv3Veqk1vOSgDjrN8zFFHmqbo/9UTYkO1h4BpfIr/1O3PPmEOiLP4hop4lr4/hGES42vuilYRewuHUQXWIu/X7hy/DWTJnd+U+v3PlaVPV/cU3tePwo4wU3t+516F3oUJkXS9Kg7W9LSgLbUW+57mnvuJOSwr8/Dp6xiTMYT81bfr4S4W4S/LxLJ4GYXpmtzmHMXR/H"
}

resource "aws_instance" "jumpbox" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.jumpbox_sg.id]
  subnet_id                   = var.public_subnet_ids[0]
  iam_instance_profile        = aws_iam_instance_profile.jumpbox_instance_profile.id
  key_name                    = aws_key_pair.noq_key.id

  credit_specification {
    cpu_credits = "unlimited"
  }

  root_block_device {
    encrypted = true
  }

  metadata_options {
    http_tokens   = "required"
    http_endpoint = "enabled"
  }
}

#Instance Role
resource "aws_iam_role" "jumpbox_role" {
  name               = "${var.cluster_id}-jumpboxInstanceRole"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

#Instance Profile
resource "aws_iam_instance_profile" "jumpbox_instance_profile" {
  name = "${var.cluster_id}-jumpboxInstanceRole"
  role = aws_iam_role.jumpbox_role.id
}

#Attach Policies to Instance Role
resource "aws_iam_policy_attachment" "jumpbox_ssm_policy_1" {
  name       = "${var.cluster_id}-ssm-attachment_1"
  roles      = [aws_iam_role.jumpbox_role.id]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_policy_attachment" "jumpbox_ssm_policy_2" {
  name       = "${var.cluster_id}-ssm-attachment_2"
  roles      = [aws_iam_role.jumpbox_role.id]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforSSM"
}