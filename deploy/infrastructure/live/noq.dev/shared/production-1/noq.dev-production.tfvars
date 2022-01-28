namespace  = "shared"
zone       = "noq.dev"
stage      = "staging"
attributes = 1
domain_name= "*.noq.dev"

noq_core   = true
region     = "us-west-2"
subnet_azs = ["us-west-2a", "us-west-2b"]

# Note tags cannot have variable names.
# Name: {namespace}.{zone}
# Environment: {stage}
tags = {
    "Name": "shared.noq.dev",
    "Environment": "production",
}

allowed_inbound_cidr_blocks = [
    "70.187.228.241/32",
    "75.164.84.226/32",  # Matt
    "75.164.48.220/32"
]

# Can be extended by adding regions to the list below
dynamo_table_replica_regions = ["us-west-2"]

# Redis
redis_node_type = "cache.t3.small"

profile = "noq_prod"