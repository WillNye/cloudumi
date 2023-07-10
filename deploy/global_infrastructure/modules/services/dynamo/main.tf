resource "aws_dynamodb_table" "tenant_details" {
  attribute {
    name = "name"
    type = "S"
  }
  attribute {
    name = "noq_cluster"
    type = "S"
  }
  name           = "tenant_details"
  hash_key       = "name"
  read_capacity  = 5
  write_capacity = 1
  global_secondary_index {
    name            = "cluster-sharding-index"
    hash_key        = "noq_cluster"
    range_key       = "name"
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
    ignore_changes = [write_capacity, read_capacity, global_secondary_index]
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
  source            = "snowplow-devops/dynamodb-autoscaling/aws"
  table_name        = aws_dynamodb_table.tenant_details.id
  read_min_capacity = 5
}
