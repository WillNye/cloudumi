module "network_label" {
  source       = "git::https://github.com/cloudposse/terraform-terraform-label.git"
  namespace    = var.namespace
  stage        = var.stage
  delimiter    = var.delimiter
  convert_case = var.convert_case
  tags         = var.default_tags
  enabled      = "true"
}

module "security_group_label" {
  source       = "git::https://github.com/cloudposse/terraform-terraform-label.git"
  namespace    = var.namespace
  stage        = var.stage
  attributes   = ["sg"]
  delimiter    = var.delimiter
  convert_case = var.convert_case
  tags         = var.default_tags
  enabled      = "true"
}