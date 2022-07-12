# Associated account id
account_id  = "306086318698"
stage       = "prod"
domain_name = "*.noq.dev"

profile = "noq_global_prod"
region  = "us-west-2"

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.dev",
  "Environment" : "production",
}

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]
s3_access_log_bucket         = "s3-access-logs.306086318698.us-west-2"