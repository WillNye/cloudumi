resource "aws_dynamodb_table" "cloudumi_identity_groups_multitenant_v2" {
  attribute {
    name = "group_id"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_identity_groups_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "group_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_cloudtrail_multitenant_v2" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_cloudtrail_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "request_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant-arn-index"
    hash_key        = "tenant"
    range_key       = "arn"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_config_multitenant_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_config_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_identity_requests_multitenant_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_identity_requests_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "request_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_policy_requests_multitenant_v2" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_policy_requests_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "request_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "arn-tenant-index"
    hash_key        = "tenant"
    range_key       = "arn"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_notifications_multitenant_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "predictable_id"
    type = "S"
  }
  name             = "${var.cluster_id}_cloudumi_notifications_multitenant_v2"
  hash_key         = "tenant"
  range_key        = "predictable_id"
  billing_mode     = "PAY_PER_REQUEST"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_users_multitenant_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "username"
    type = "S"
  }
  name             = "${var.cluster_id}_cloudumi_users_multitenant_v2"
  hash_key         = "tenant"
  range_key        = "username"
  billing_mode     = "PAY_PER_REQUEST"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_tenant_static_configs_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_tenant_static_configs_v2"
  hash_key     = "tenant"
  range_key    = "id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_identity_users_multitenant_v2" {
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "user_id"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_identity_users_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "user_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "noq_api_keys_v2" {
  attribute {
    name = "api_key"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name         = "${var.cluster_id}_noq_api_keys_v2"
  hash_key     = "tenant"
  range_key    = "api_key"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "tenant_id_index"
    hash_key        = "tenant"
    range_key       = "id"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  # we are ignoring the life cycle because
  # there is no way to get around the read_capacity, write_capacity
  # drift of GSI
  # see https://github.com/hashicorp/terraform-provider-aws/issues/671
  lifecycle { ignore_changes = [global_secondary_index] }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_iamroles_multitenant_v2" {
  attribute {
    name = "entity_id"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_iamroles_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "entity_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "noq_aws_accounts_v2" {
  attribute {
    name = "aws_account_id"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  name         = "${var.cluster_id}_noq_aws_accounts_v2"
  hash_key     = "tenant"
  range_key    = "aws_account_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "aws_account_id_index"
    hash_key        = "aws_account_id"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_resource_cache_multitenant_v2" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "entity_id"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  name         = "${var.cluster_id}_cloudumi_resource_cache_multitenant_v2"
  hash_key     = "tenant"
  range_key    = "entity_id"
  billing_mode = "PAY_PER_REQUEST"
  global_secondary_index {
    name            = "tenant-arn-index"
    hash_key        = "tenant"
    range_key       = "arn"
    projection_type = "ALL"
  }
  global_secondary_index {
    name            = "tenant-index"
    hash_key        = "tenant"
    projection_type = "ALL"
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}
