

resource "aws_security_group" "vpc_to_dax_sg" {
  name        = "${var.namespace}-ecs-dax-access"
  description = "Gives access to the DAX cluster for resources on the VPC."
  vpc_id      = aws_vpc.main_vpc.id

  ingress {
    description = "Allow communication for the DAX cluster"
    from_port   = 8811
    to_port     = 9911
    protocol    = "TCP"
    cidr_blocks = [aws_vpc.main_vpc.cidr_block]
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