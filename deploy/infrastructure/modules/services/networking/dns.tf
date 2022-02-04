data "aws_route53_zone" "tenant_zone" {
  name         = var.zone
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.tenant_zone.zone_id
  name    = var.domain_name
  type    = "CNAME"
  ttl     = "300"
  records = [aws_lb.noq_api_load_balancer.dns_name]
}