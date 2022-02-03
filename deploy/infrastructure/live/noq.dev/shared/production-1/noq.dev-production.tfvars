// AWS_PROFILE=noq_dev terraform plan -var-file="staging.tfvars"
noq_core   = true
region     = "us-west-2"
stage      = "prod"
namespace  = "noq"
attributes = 1
subnet_azs = ["us-west-2a", "us-west-2b"]
domain_name = "*.noq.dev"

environment_tag = "noq.core"

allowed_inbound_cidr_blocks = ["70.187.228.241/32", "75.164.48.220/32"]

# Redis
redis_node_type = "cache.t3.small"

# Sentry
sentry_dsn = "https://b56872bca2c548cb9200121ae436b87d@o1134078.ingest.sentry.io/6181194"