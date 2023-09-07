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
# `localhost` needed for testing, as we need to hit the tenant_registration endpoint through localhost
landing_page_domains = ["shared.staging.noq.dev", "localhost"]
profile              = "staging/staging_admin"

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
  "0.0.0.0/0"
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Dax
dax_node_type  = "dax.t3.medium"
dax_node_count = 1

# SES
notifications_mail_from_domain = "ses-us-west-2.staging.noq.dev"
notifications_sender_identity  = "notifications@noq.dev"

# Redis
redis_node_type            = "cache.t3.micro"
secret_manager_secret_name = "shared-staging-noq_secrets"

# RDS
noq_db_database_name = "noq"
noq_db_instance_type = "db.t4g.medium"

# # Sentry
# sentry_dsn = "https://replaceme@replaceme.ingest.sentry.io/replaceme"

s3_access_log_bucket         = "s3-access-logs.259868150464.us-west-2"
elasticache_node_type        = "cache.t3.micro"
google_analytics_tracking_id = "replaceme"

# Global info
global_tenant_data_account_id = "615395543222"
legal_docs_bucket_name        = "noq-global-staging-legal-docs"

# Task counts
api_count    = 1
worker_count = 0

log_expiry = 365