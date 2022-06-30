resource "aws_dynamodb_table" "cloudumi_identity_groups_multitenant" {
  attribute {
    name = "group_id"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_identity_groups_multitenant"
  hash_key       = "host"
  range_key      = "group_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_cloudtrail_multitenant" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_cloudtrail_multitenant"
  hash_key       = "host"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host-arn-index"
    hash_key        = "host"
    range_key       = "arn"
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_config_multitenant" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_config_multitenant"
  hash_key       = "host"
  range_key      = "id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_identity_requests_multitenant" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_identity_requests_multitenant"
  hash_key       = "host"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_policy_requests_multitenant" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "request_id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_policy_requests_multitenant"
  hash_key       = "host"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "arn-host-index"
    hash_key        = "host"
    range_key       = "arn"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_notifications_multitenant" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "predictable_id"
    type = "S"
  }
  name             = "${var.cluster_id}_cloudumi_notifications_multitenant"
  hash_key         = "host"
  range_key        = "predictable_id"
  read_capacity    = 1
  write_capacity   = 1
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_users_multitenant" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "username"
    type = "S"
  }
  name             = "${var.cluster_id}_cloudumi_users_multitenant"
  hash_key         = "host"
  range_key        = "username"
  read_capacity    = 1
  write_capacity   = 1
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_tenant_static_configs" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_tenant_static_configs"
  hash_key       = "host"
  range_key      = "id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_identity_users_multitenant" {
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "user_id"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_identity_users_multitenant"
  hash_key       = "host"
  range_key      = "user_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "noq_api_keys" {
  attribute {
    name = "api_key"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  attribute {
    name = "id"
    type = "S"
  }
  name           = "${var.cluster_id}_noq_api_keys"
  hash_key       = "host"
  range_key      = "api_key"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  global_secondary_index {
    name            = "host_id_index"
    hash_key        = "host"
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_iamroles_multitenant" {
  attribute {
    name = "entity_id"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_iamroles_multitenant"
  hash_key       = "host"
  range_key      = "entity_id"
  read_capacity  = 1
  write_capacity = 10
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "noq_aws_accounts" {
  attribute {
    name = "aws_account_id"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  name           = "${var.cluster_id}_noq_aws_accounts"
  hash_key       = "host"
  range_key      = "aws_account_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host_index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  global_secondary_index {
    name            = "aws_account_id_index"
    hash_key        = "aws_account_id"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}

resource "aws_dynamodb_table" "cloudumi_resource_cache_multitenant" {
  attribute {
    name = "arn"
    type = "S"
  }
  attribute {
    name = "entity_id"
    type = "S"
  }
  attribute {
    name = "host"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_resource_cache_multitenant"
  hash_key       = "host"
  range_key      = "entity_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "host-arn-index"
    hash_key        = "host"
    range_key       = "arn"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  global_secondary_index {
    name            = "host-index"
    hash_key        = "host"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}


module "table_autoscaling_1" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_groups_multitenant.id
}

module "table_autoscaling_2" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_cloudtrail_multitenant.id
}

module "table_autoscaling_3" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_config_multitenant.id
}

module "table_autoscaling_4" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_requests_multitenant.id
}

module "table_autoscaling_5" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_policy_requests_multitenant.id
}
module "table_autoscaling_6" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_notifications_multitenant.id
}
module "table_autoscaling_7" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_tenant_static_configs.id
}
module "table_autoscaling_8" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_users_multitenant.id
}

module "table_autoscaling_9" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.noq_api_keys.id
}

module "table_autoscaling_10" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name         = aws_dynamodb_table.cloudumi_iamroles_multitenant.id
  write_min_capacity = 10
}

module "table_autoscaling_11" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.noq_aws_accounts.id
}
module "table_autoscaling_12" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_resource_cache_multitenant.id
}

// V1 resources end

// V2 resources start

resource "aws_dynamodb_table" "cloudumi_identity_groups_multitenant_v2" {
  attribute {
    name = "group_id"
    type = "S"
  }
  attribute {
    name = "tenant"
    type = "S"
  }
  name           = "${var.cluster_id}_cloudumi_identity_groups_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "group_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_cloudtrail_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant-arn-index"
    hash_key        = "tenant"
    range_key       = "arn"
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_config_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_identity_requests_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_policy_requests_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "request_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "arn-tenant-index"
    hash_key        = "tenant"
    range_key       = "arn"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  read_capacity    = 1
  write_capacity   = 1
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  read_capacity    = 1
  write_capacity   = 1
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_tenant_static_configs_v2"
  hash_key       = "tenant"
  range_key      = "id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_identity_users_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "user_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_noq_api_keys_v2"
  hash_key       = "tenant"
  range_key      = "api_key"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_iamroles_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "entity_id"
  read_capacity  = 1
  write_capacity = 10
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 10
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

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_noq_aws_accounts_v2"
  hash_key       = "tenant"
  range_key      = "aws_account_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant_index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  global_secondary_index {
    name            = "aws_account_id_index"
    hash_key        = "aws_account_id"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

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
  name           = "${var.cluster_id}_cloudumi_resource_cache_multitenant_v2"
  hash_key       = "tenant"
  range_key      = "entity_id"
  read_capacity  = 1
  write_capacity = 1
  global_secondary_index {
    name            = "tenant-arn-index"
    hash_key        = "tenant"
    range_key       = "arn"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  global_secondary_index {
    name            = "tenant-index"
    hash_key        = "tenant"
    projection_type = "ALL"
    read_capacity   = 1
    write_capacity  = 1
  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # dynamic "replica" {
  #   for_each = var.dynamo_table_replica_regions
  #   content {
  #     region_name = replica.value
  #   }
  # }

  lifecycle {
    ignore_changes = [write_capacity, read_capacity]
  }

  tags = merge(
    var.tags,
    {}
  )

  point_in_time_recovery {
    enabled = true
  }

}


module "table_autoscaling_v2_1" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_groups_multitenant_v2.id
}

module "table_autoscaling_v2_2" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_cloudtrail_multitenant_v2.id
}

module "table_autoscaling_v2_3" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_config_multitenant_v2.id
}

module "table_autoscaling_v2_4" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_requests_multitenant_v2.id
}

module "table_autoscaling_v2_5" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_policy_requests_multitenant_v2.id
}
module "table_autoscaling_v2_6" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_notifications_multitenant_v2.id
}
module "table_autoscaling_v2_7" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_tenant_static_configs_v2.id
}
module "table_autoscaling_v2_8" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_identity_users_multitenant_v2.id
}

module "table_autoscaling_v2_9" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.noq_api_keys_v2.id
}

module "table_autoscaling_v2_10" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name         = aws_dynamodb_table.cloudumi_iamroles_multitenant_v2.id
  write_min_capacity = 10
}

module "table_autoscaling_v2_11" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.noq_aws_accounts_v2.id
}
module "table_autoscaling_v2_12" {
  source = "snowplow-devops/dynamodb-autoscaling/aws"

  table_name = aws_dynamodb_table.cloudumi_resource_cache_multitenant_v2.id
}