data "aws_route53_zone" "tenant_zone" {
  name         = var.domain_name
  private_zone = false
}