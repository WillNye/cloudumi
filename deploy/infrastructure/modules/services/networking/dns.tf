resource "aws_route53_zone" "tenant_zone" {
  name         = var.domain_name
}