account_id = "940552945933"

namespace   = "cyberdyne"
zone        = "noq.dev"
stage       = "prod"
attributes  = 1
domain_name = "cyberdyne.noq.dev"

noq_core   = true
region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "cyberdyne.noq.dev",
  "Environment" : "production",
}

allowed_inbound_cidr_blocks = [
  "70.187.228.241/32", # Curtis
  "75.164.6.16/32",    # Matt
  "141.239.104.37/32", # Kris
  "41.190.131.30/32",  # Kayizzi
  "189.4.79.228/32",   # Christian
  "186.209.21.192/32", # Christian 2
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Redis
redis_node_type = "cache.t3.small"

profile = "noq_prod"
# Sentry
sentry_dsn = "https://f446f0f25a74440db6e211ebe73c05f9@o1134078.ingest.sentry.io/6188334"

s3_access_log_bucket = "s3-access-logs.940552945933.us-west-2"