// AWS_PROFILE=noq_dev terraform plan -var-file="staging.tfvars"
noq_core   = true
region     = "us-west-2"
namespace  = "noq"
stage      = "staging"
attributes = 1
subnet_azs = ["us-west-2a", "us-west-2b"]
domain_name = "staging.noq.dev"

tags = {
    "Name": "noq.core",
    "Environment": "staging",
}

allowed_inbound_cidr_blocks = ["70.187.228.241/32", "75.164.48.220/32"]

# Redis
redis_node_type = "cache.t3.small"