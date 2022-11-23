# Set to true to create the ECS task role -
# this MUST ONLY BE DONE ONCE IN THE BEGINNING
# Once the ECS task role is created and we get access to environments, when it
# is deleted, so is our access to environments, NO MATTER WHAT WE NAME IT
modify_ecs_task_role = true

# Associated account id
account_id = "277516517760"

namespace   = "akasa"
zone        = "internal.akasa.engineering"
stage       = "prod"
attributes  = 2
domain_name = "noq.internal.akasa.engineering"
profile     = "akasa_deployment_role"

region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
  "Name" : "noq.internal.akasa.engineering",
  "Environment" : "production",
}

# This variable should only be set to true for NOQ Corpo accounts
# It sets up a container registry (so only for prod and staging)
noq_core = false

allowed_inbound_cidr_blocks = [
  "0.0.0.0/0"
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Dax
dax_node_type  = "dax.t3.small"
dax_node_count = 2

# SES
notifications_mail_from_domain = "ses-us-west-2.internal.akasa.engineering"

# Redis
redis_node_type            = "cache.t3.small"
secret_manager_secret_name = "akasa-prod-noq_secrets"

# Sentry
sentry_dsn                    = "https://f446f0f25a74440db6e211ebe73c05f9@o1134078.ingest.sentry.io/6188334"
notifications_sender_identity = "noq-notifications@akasa.com"

s3_access_log_bucket         = "s3-access-logs.775726381634.us-west-2"
elasticache_node_type        = "cache.t3.medium"
google_analytics_tracking_id = "G-P5K1SQF3P6"

global_tenant_data_account_id = "306086318698"
legal_docs_bucket_name        = "noq-global-prod-legal-docs"

api_count    = 1
worker_count = 1

log_expiry = 365