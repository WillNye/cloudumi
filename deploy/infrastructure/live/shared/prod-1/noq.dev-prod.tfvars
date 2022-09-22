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
profile     = "noq_prod"

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
  "0.0.0.0/0"
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Dax
dax_node_type  = "dax.t3.small"
dax_node_count = 1

# Redis
redis_node_type = "cache.t3.small"

# Sentry
sentry_dsn = "https://50b9f954977449db94bf4d1a8b9a8084@o1134078.ingest.sentry.io/6625264"

s3_access_log_bucket         = "s3-access-logs.940552945933.us-west-2"
elasticache_node_type        = "cache.t2.medium"
google_analytics_tracking_id = "G-P5K1SQF3P6"

# Global info
global_tenant_data_account_id = "306086318698"
legal_docs_bucket_name        = "noq-global-prod-legal-docs"

# Task counts
api_count    = 1
worker_count = 2
