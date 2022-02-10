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

resource "aws_network_interface" "jumpbox_network_interface" {
  subnet_id   = var.public_subnet_ids[0]

  tags = {
    Name = "jumpbox_primary_network_interface"
  }
}

resource "aws_security_group" "jumpbox-sg" {
  name        = "${var.cluster_id}-ec2-jumpbox-sg"
  description = "Allows access to the EC2 jumpbox VM."
  vpc_id      = var.vpc_id

  ingress {
    description     = "Access to jumpbox"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks     = var.allowed_inbound_cidr_blocks
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

resource "aws_instance" "jumpbox" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  associate_public_ip_address = true

  network_interface {
    network_interface_id = aws_network_interface.jumpbox_network_interface.id
    device_index         = 0
  }

  credit_specification {
    cpu_credits = "unlimited"
  }
}