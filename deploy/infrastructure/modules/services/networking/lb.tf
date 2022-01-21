# Create a new load balancer
resource "aws_elb" "noq_api_load_balancer" {
  name               = "${var.name}-${var.attributes}-lb"

  access_logs {
    bucket        = var.system_bucket
    bucket_prefix = "elb_access_logs"
    interval      = 60
  }

  listener {
    instance_port      = 8000
    instance_protocol  = "http"
    lb_port            = var.lb_port
    lb_protocol        = "https"
    ssl_certificate_id = aws_acm_certificate_validation.tenant_certificate_validation.certificate_arn
  }

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    target              = "HTTP:8000/"
    interval            = 30
  }

  subnets = [aws_subnet.subnet_public.id]
  cross_zone_load_balancing   = true
  idle_timeout                = 400
  connection_draining         = true
  connection_draining_timeout = 400

  tags = merge(
    var.tags,
    {
      Name = "noq_api_load_balancer"
    }
  )
}

# For the public load balancer
resource "aws_security_group" "lb-sg" {
  name        = "allow_access_to_noq"
  description = "Allows access to the load balancer, which forwards to the CloudUmi server."
  vpc_id      = aws_vpc.main_vpc.id

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

  tags = merge(
    var.tags,
    {
      Name = "allow_access_to_noq"
    }
  )
}