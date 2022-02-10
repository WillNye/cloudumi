account_id = "259868150464"

namespace   = "shared"
zone        = "staging.noq.dev"
stage       = "staging"
attributes  = 1
domain_name = "*.staging.noq.dev"

noq_core   = true
region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "shared.noq.dev",
  "Environment" : "staging",
}

allowed_inbound_cidr_blocks = [
  "70.187.228.241/32", # Curtis
  "75.164.6.16/32",    # Matt
  "75.164.48.220/32"
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Redis
redis_node_type = "cache.t3.small"

profile = "noq_dev"
# Sentry
sentry_dsn = "https://fb6ce9063023416592859491f2498fba@o1134078.ingest.sentry.io/6181191"

s3_access_log_bucket = "s3-access-logs.259868150464.us-west-2"