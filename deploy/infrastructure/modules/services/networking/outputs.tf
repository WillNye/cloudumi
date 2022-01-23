output "igw_arn" {
  description = "The main igw ARN"
  value = aws_internet_gateway.main_igw.arn
}

output "load_balancer_endpoint" {
  description = "The endpoint URI of the load balancer configured to be used in the NOQ configuration files"
  value = aws_lb.noq_api_load_balancer.dns_name
}

output "target_group_arn" {
  description = "The target group ARN, needs to be updated in the BUILD file under the ecs-cli call"
  value = aws_lb_target_group.noq_api_balancer_target_group.arn
}

output "vpc_arn" {
  description = "The main VPC ARN"
  value = aws_vpc.main_vpc.arn
}

output "vpc_cidr_range" {
  description = "The CIDR range of the VPC"
  value = aws_vpc.main_vpc.cidr_block
}

output "vpc_id" {
  description = "The ID of the VPC generated"
  value = aws_vpc.main_vpc.id
}

output "vpc_subnet_public_cidr" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value = aws_subnet.subnet_public.cidr_block
}

output "vpc_subnet_private_cidr" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value = aws_subnet.subnet_private.cidr_block
}

output "vpc_subnet_public_id" {
  description = "The public CIDR range of the subnet assigned to the VPC"
  value = aws_subnet.subnet_public.id
}

output "vpc_subnet_private_id" {
  description = "The private CIDR range of the private subnet assign to the VPC"
  value = aws_subnet.subnet_private.id
}