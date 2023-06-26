# Associated account id
account_id  = "350876197038"
stage       = "dev"
domain_name = "*.example.com"

profile = "development_2/development_2_admin"
region  = "us-west-2"

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.dev",
  "Environment" : "development",
}

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]
s3_access_log_bucket         = "noq-global-dev-s3-access-logs.us-west-2"