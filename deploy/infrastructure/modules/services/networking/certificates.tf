resource "aws_acm_certificate" "tenant_certificate" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = merge(
    var.tags,
    {
      "Environment": var.cluster_id
    }
  )


  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "tenant_domain_records" {
  for_each = {
    for dvo in aws_acm_certificate.tenant_certificate.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.tenant_zone.zone_id

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_acm_certificate_validation" "tenant_certificate_validation" {
  timeouts {
    create = var.timeout
  }
  certificate_arn         = aws_acm_certificate.tenant_certificate.arn
  validation_record_fqdns = [for record in aws_route53_record.tenant_domain_records : record.fqdn]

  tags = merge(
    var.tags,
    {}
  )
}