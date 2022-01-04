// AWS_PROFILE=noq_dev terraform plan -var-file="staging.tfvars"
region     = "us-west-2"
stage      = "staging"
attributes = 1
subnet_azs = ["us-west-2a", "us-west-2b"]

allowed_inbound_cidr_blocks = ["70.187.228.241/32", "75.164.48.220/32"]