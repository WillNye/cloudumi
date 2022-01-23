# Create a new load balancer
resource "aws_lb" "noq_api_load_balancer" {
  name               = "${var.name}-${var.attributes}-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb-sg.id]
  subnets            = [aws_subnet.subnet_public_az0.id, aws_subnet.subnet_public_az1.id]

  enable_deletion_protection = true

  access_logs {
    bucket        = var.system_bucket
  }

  tags = merge(
    var.tags,
    {
      Name = "noq_api_load_balancer"
    }
  )
}

resource "aws_lb_target_group" "noq_api_balancer_target_group" {
  name     = "${var.name}-${var.attributes}-lb"
  port     = 8092
  protocol = "HTTP"
  vpc_id   = aws_vpc.main_vpc.id
}

resource "aws_lb_listener" "noq_api_balancer_front_end_80_redirect" {
  load_balancer_arn = aws_lb.noq_api_load_balancer.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "noq_api_balancer_front_end_443" {
  load_balancer_arn = aws_lb.noq_api_load_balancer.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate_validation.tenant_certificate_validation.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.noq_api_balancer_target_group.arn
  }
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