# Associated account id
account_id  = "615395543222"
stage       = "staging"
domain_name = "*.staging.noq.dev"

profile = "noq_global_staging"
region  = "us-west-2"

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.dev",
  "Environment" : "staging",
}

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]
s3_access_log_bucket         = "noq-global-staging-s3-access-logs"

github_app_noq_secret_arn = "arn:aws:secretsmanager:us-west-2:615395543222:secret:global-staging/github-app-noq-bjogHH"