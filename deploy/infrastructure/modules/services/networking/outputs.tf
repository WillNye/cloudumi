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