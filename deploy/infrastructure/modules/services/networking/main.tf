module "network" {
  source = "github.com/terraform-aws-modules/terraform-aws-vpc"

  name = module.network_label.id
  cidr = var.vpc_cidr
  azs  = var.subnet_azs

  enable_nat_gateway                 = true
  enable_vpn_gateway                 = true
  propagate_public_route_tables_vgw  = true
  propagate_private_route_tables_vgw = true
  create_database_subnet_group       = false
  enable_dhcp_options                = true
  enable_dns_hostnames               = true
  enable_dns_support                 = true
  #  enable_s3_endpoint                 = true
  #  enable_dynamodb_endpoint           = true
  tags                  = var.default_tags
  create_vpc            = true
  public_subnet_suffix  = "public-subnet"
  public_subnets        = var.public_subnet_cidrs
  private_subnet_suffix = "private-subnet"
  private_subnets       = var.private_subnet_cidrs
}

resource "aws_security_group" "server" {
  vpc_id      = module.network.vpc_id
  name        = module.security_group_label.id
  description = "Allow ingress from authorized IPs to self, and egress to everywhere."
  tags        = module.security_group_label.tags
}

# Create a new load balancer
resource "aws_elb" "noq_api_load_balancer" {
  name               = "${var.cluster_id}_load_balancer"
  availability_zones = var.subnet_azs

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
    ssl_certificate_id = module.aws_acm_certificate_validation.arn
  }

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    target              = "HTTP:8000/"
    interval            = 30
  }

  instances                   = [aws_instance.foo.id]
  cross_zone_load_balancing   = true
  idle_timeout                = 400
  connection_draining         = true
  connection_draining_timeout = 400

  tags = {
    Name = "foobar-terraform-elb"
  }
}

resource "aws_lb_listener_certificate" "example" {
  listener_arn    = aws_elb.listener.front_end.arn
  certificate_arn = aws_acm_certificate.example.arn
}

# For the public load balancer
resource "aws_security_group" "lb-sg" {
  name        = "allow_access_to_noq"
  description = "Allows access to the load balancer, which forwards to the CloudUmi server."
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