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
s3_access_log_bucket         = "noq-global-prod-s3-access-logs.us-west-2"

github_app_noq_secret_arn = "arn:aws:secretsmanager:us-west-2:306086318698:secret:global-prod/github-app-noq-MdxtTr"
