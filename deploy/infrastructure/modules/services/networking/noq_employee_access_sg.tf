resource "aws_security_group" "noq_employees_sg" {
  name        = "${var.namespace}-noq-employee-access"
  description = "Gives NOQ Employees network access to a resource with this Security Group."
  vpc_id      = aws_vpc.main_vpc.id

  ingress {
    description = "Full ingress access"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.noq_employee_cidr_blocks
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