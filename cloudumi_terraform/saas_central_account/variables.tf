# ---------------------------------------------------------------------------------------------------------------------
# GENERAL
# These variables pass in general data from the calling module, such as the AWS Region and billing tags.
# ---------------------------------------------------------------------------------------------------------------------


variable "bucket_name_prefix" {
  description = "The prefix to use for the S3 bucket name. This will be used to create the S3 bucket name. The bucket name will be the prefix + cluster ID."
  type        = string
  default     = "cloudumi-cache"
}

variable "namespace" {
  description = "Namespace, which could be your organization name. It will be used as the first item in naming sequence."
  default     = "noq"
  type        = string
}

variable "capacity_providers" {
  description = "List of short names of one or more capacity providers to associate with the cluster. Valid values also include FARGATE and FARGATE_SPOT."
  type        = list(string)
  default     = ["FARGATE_SPOT", "FARGATE"]
}


variable "stage" {
  description = "Stage, e.g. `prod`, `staging`, `dev`, or `test`. Second item in naming sequence."
}

variable "cluster_id" {
  description = "The cluster ID for CloudUmi."
  type        = string
}

variable "container_insights" {
  description = "Controls if ECS Cluster has container insights enabled"
  type        = bool
  default     = false
}

variable "default_tags" {
  description = "Default billing tags to be applied across all resources"
  type        = map(string)
  default     = {}
}

variable "region" {
  description = "The AWS region for these resources, such as us-east-1."
}

# ---------------------------------------------------------------------------------------------------------------------
# TOGGLES
# Toogle to true to create resources
# ---------------------------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------------------------
# RESOURCE VALUES
# These variables pass in actual values to configure resources. CIDRs, Instance Sizes, etc.
# ---------------------------------------------------------------------------------------------------------------------
variable "email_addresses" {
  type = list(string)
  default = [
    "email_address_here@example.com"
  ]
  description = ""
}

variable "your_ses_identity" {
  type        = string
  default     = "your_identity.example.com"
  description = ""
}

##### Networking
variable "vpc_cidr" {
  description = "The CIDR block for the VPC."
  type        = string
  default     = "10.1.1.0/24"

}
// variable "subnet_azs" {
//   description = "Subnets will be created in these availability zones (need at least two for load balancer)."
//   type        = list(string)

// }

variable "public_subnet_cidrs" {
  description = "The CIDR block of the subnet the load balancer will be placed in."
  type        = list(string)
  default     = ["10.1.1.128/28", "10.1.1.144/28"] # LB requires at least two networks
}


variable "private_subnet_cidrs" {
  description = "The CIDR block of the subnet the ConsoleMe server will be placed in."
  type        = list(string)
  default     = ["10.1.1.0/28"]
}

variable "allowed_inbound_cidr_blocks" {
  description = "Allowed inbound CIDRs for the security group rules."
  default     = []
  type        = list(string)
}

variable "allow_internet_access" {
  description = "Set to true to allow Internet access to the ConsoleMe server."
  default     = false
  type        = bool
}

variable "lb_port" {
  description = "The port the load balancer will listen on."
  default     = 443
}

# Compute
variable "instance_type" {
  description = "The size of the Ec2 instance. Defaults to t2.medium"
  default     = "t2.medium"
}

variable "volume_size" {
  description = "The disk size for the EC2 instance root volume. Defaults to 50 (for 50GB)"
  default     = 50
}

variable "custom_user_data_script" {
  description = "Additional userdata to pass in at runtime"
  default     = ""
}

# ---------------------------------------------------------------------------------------------------------------------
# RESOURCE REFERENCES
# These variables pass in metadata on other AWS resources, such as ARNs, Names, etc.
# ---------------------------------------------------------------------------------------------------------------------
variable "ec2_ami_owner_filter" {
  description = "List of AMI owners to limit search. Defaults to `amazon`."
  default     = "amazon"
  type        = string
}

variable "ec2_ami_name_filter" {
  description = "The name of the AMI to search for. Defaults to amzn2-ami-hvm-2.0.2020*-x86_64-ebs"
  default     = "amzn2-ami-hvm-2.0.2020*-x86_64-ebs" # Need a release post Jan 2020 to support IMDSv2
  type        = string
}


# ---------------------------------------------------------------------------------------------------------------------
# NAMING
# This manages the names of resources in this module.
# ---------------------------------------------------------------------------------------------------------------------



variable "attributes" {
  type        = list(string)
  default     = []
  description = "Additional attributes, e.g. `1`"
}

variable "convert_case" {
  description = "Convert fields to lower case"
  default     = "true"
}

variable "delimiter" {
  type        = string
  default     = "-"
  description = "Delimiter to be used between (1) `namespace`, (2) `name`, (3) `stage` and (4) `attributes`"
}

variable "consoleme_instance_profile_name" {
  default = "consolemeInstanceProfile"
}

variable "kms_key_alias" {
  description = "The KMS key alias to use for the EBS Volume"
  default     = "alias/consoleme"
}

variable "sync_accounts_from_organizations" {
  description = "Sync accounts from AWS organizations?"
  default     = false
}

variable "sync_accounts_from_organizations_account_map" {
  type        = list(map(string))
  description = "Organizations master account ID"
  default     = []
}

variable "subnet_azs" {
  description = "Subnets will be created in these availability zones (need at least two for load balancer)."
  type        = list(string)

}


