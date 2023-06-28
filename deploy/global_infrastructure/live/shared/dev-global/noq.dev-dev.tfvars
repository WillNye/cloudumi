# Associated account id
account_id  = "759357822767"
stage       = "dev"
domain_name = "*.dev.noq.dev"

profile = "development/development_admin"
region  = "us-west-2"

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.dev",
  "Environment" : "dev",
}

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]
s3_access_log_bucket         = "noq-global-staging-s3-access-logs"

github_app_noq_webhook_secret_arn = "arn:aws:secretsmanager:us-west-2:759357822767:secret:global-dev/github-app-noq-dev-webhook-secret-037YW9"
