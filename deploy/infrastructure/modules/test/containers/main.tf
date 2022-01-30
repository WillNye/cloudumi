resource "aws_ecs_task_definition" "test_task_definition" {
  family = "service"
  container_definitions = jsonencode([
    {
      name      = "${var.ecs_cluster_name}-api"
      image     = "259868150464.dkr.ecr.${var.region}.amazonaws.com/${var.stage}-registry-api:${var.stage}"
      cpu       = 1
      memory    = 2048
      essential = true
      portMappings = [
        {
          containerPort = 8092
          hostPort      = 8092
        }
      ]
    },
    {
      name      = "${var.ecs_cluster_name}-celery"
      image     = "259868150464.dkr.ecr.${var.region}.amazonaws.com/${var.stage}-registry-celery:${var.stage}"
      cpu       = 1
      memory    = 2048
      essential = true
    },
  ])
}
  
resource "aws_ecs_service" "test_service" {
  name            = "${var.ecs_cluster_name}_test"
  cluster         = var.ecs_cluster_name
  task_definition = aws_ecs_task_definition.test_task_definition.arn
  desired_count   = 1
  enable_execute_command = true
  iam_role        = var.ecs_task_execution_role

  ordered_placement_strategy {
    type  = "binpack"
    field = "cpu"
  }
}