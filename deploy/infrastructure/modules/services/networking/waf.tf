resource "aws_wafv2_web_acl" "web-acl" {
  name        = "${var.cluster_id}-web-acl"
  description = "${var.cluster_id}-web-acl"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 0

    override_action {
      none {} # quarks of WAFv2 API
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    priority = 1

    override_action {
      none {} # quarks of WAFv2 API
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesLinuxRuleSet"
    priority = 2

    override_action {
      none {} # quarks of WAFv2 API
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesLinuxRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesLinuxRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {} # quarks of WAFv2 API
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = false
    metric_name                = "${var.cluster_id}-web-acl"
    sampled_requests_enabled   = true
  }

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_wafv2_web_acl_association" "web-acl-cloudumi-association" {
  resource_arn = aws_lb.noq_api_load_balancer.arn
  web_acl_arn  = aws_wafv2_web_acl.web-acl.arn
}

resource "aws_cloudwatch_log_group" "web-acl" {
  name              = "aws-waf-logs-cloudumi-${var.cluster_id}"
  retention_in_days = 365
}

resource "aws_wafv2_web_acl_logging_configuration" "web-acl" {
  log_destination_configs = [aws_cloudwatch_log_group.web-acl.arn]
  resource_arn            = aws_wafv2_web_acl.web-acl.arn
  redacted_fields {
    single_header {
      name = "noq_auth"
    }
  }
}