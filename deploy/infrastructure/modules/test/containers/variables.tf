variable "ecs_cluster_name" {
  description = "The ecs test cluster is an output of the main deploy terraform setup"
  type = string
}

variable "ecs_task_execution_role" {
  description = "The task IAM execution role"
  type = string
}

variable "region" {
  description = "The region set as per the output"
  type = string
}

variable "stage" {
  description = "The stage set as per the output"
  type = string
}