variable "ecs_cluster_name" {
  description = "The ecs test cluster is an output of the main deploy terraform setup"
  type = string
}

variable "ecs_task_execution_role" {
  description = "The task IAM execution role"
  type = string
}