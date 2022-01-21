output "load_balancer_endpoint" {
  description = "The endpoint URI of the load balancer configured to be used in the NOQ configuration files"
  value = aws_elb.noq_api_load_balancer.dns_name
}

output "vpc_arn" {
  description = "The main VPC ARN"
  value = aws_vpc.main_vpc.arn
}

output "igw_arn" {
  description = "The main igw ARN"
  value = aws_internet_gateway.main_igw.arn
}

output "vpc_cidr_range" {
  description = "The CIDR range of the VPC"
  value = aws_vpc.main_vpc.cidr_block
}

output "vpc_subnet_public" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value = aws_subnet.subnet_public.cidr_block
}

output "vpc_subnet_private" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value = aws_subnet.subnet_private.cidr_block
}