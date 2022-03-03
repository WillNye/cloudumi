# Set to true to create the ECS task role -
# this MUST ONLY BE DONE ONCE IN THE BEGINNING
# Once the ECS task role is created and we get access to environments, when it
# is deleted, so is our access to environments, NO MATTER WHAT WE NAME IT
modify_ecs_task_role = false

# Associated account id
account_id = "940552945933"

namespace   = "shared"
zone        = "noq.dev"
stage       = "prod"
attributes  = 1
domain_name = "*.noq.dev"

region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.dev",
  "Environment" : "production",
}

# This variable should only be set to true for NOQ Corpo accounts
# It sets up a container registry (so only for prod and staging)
noq_core = true

allowed_inbound_cidr_blocks = [
  "70.187.228.241/32", # Curtis
  "141.239.104.37/32", # Kris
  "41.190.131.30/32",  # Kayizzi
  "189.4.79.228/32",   # Christian
  "186.209.21.192/32", # Christian 2
  "75.164.90.80/32",   # Matt
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Redis
redis_node_type = "cache.t3.small"

profile = "noq_prod"
# Sentry
sentry_dsn = "https://b56872bca2c548cb9200121ae436b87d@o1134078.ingest.sentry.io/6181194"

s3_access_log_bucket = "s3-access-logs.940552945933.us-west-2"