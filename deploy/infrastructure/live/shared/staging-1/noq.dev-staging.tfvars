# Set to true to create the ECS task role -
# this MUST ONLY BE DONE ONCE IN THE BEGINNING
# Once the ECS task role is created and we get access to environments, when it
# is deleted, so is our access to environments, NO MATTER WHAT WE NAME IT
modify_ecs_task_role = false

# Associated account id
account_id = "259868150464"

# General cluster metadata
namespace   = "shared"
zone        = "staging.noq.dev"
stage       = "staging"
attributes  = 1
domain_name = "*.staging.noq.dev"

region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "shared.noq.dev",
  "Environment" : "staging",
}

# This variable should only be set to true for NOQ Corpo accounts
# It sets up a container registry (so only for prod and staging)
noq_core = true

allowed_inbound_cidr_blocks = [
  "70.187.228.241/32", # Curtis
  "75.164.6.16/32",    # Matt
  "75.164.48.220/32",
  "141.239.104.37/32", # Kris
  "41.190.131.30/32",  # Kayizzi
  "189.4.79.228/32",   # Christian
  "186.209.21.192/32", # Christian 2
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Redis
redis_node_type = "cache.t3.small"

profile = "noq_staging"
# Sentry
sentry_dsn = "https://fb6ce9063023416592859491f2498fba@o1134078.ingest.sentry.io/6181191"

s3_access_log_bucket = "s3-access-logs.259868150464.us-west-2"

elasticache_node_type = "cache.t3.micro"