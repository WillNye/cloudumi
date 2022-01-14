output "load_balancer_endpoint" {
  description = "The endpoint URI of the load balancer configured to be used in the NOQ configuration files"
  value = aws_elb.noq_api_load_balancer.dns_name
}