resource "aws_security_group" "server" {
  vpc_id      = module.network.vpc_id
  name        = module.security_group_label.id
  description = "Allow ingress from authorized IPs to self, and egress to everywhere."
  tags        = module.security_group_label.tags
}


# For the public load balancer
resource "aws_security_group" "lb-sg" {
  name        = "allow_access_to_noq"
  description = "Allows access to the load balancer, which forwards to the ConsoleMe server."
  vpc_id      = module.network.vpc_id

  ingress {
    description = "HTTPS for accessing Noq"
    from_port   = var.lb_port
    to_port     = var.lb_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_inbound_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "allow_access_to_noq"
  }
}