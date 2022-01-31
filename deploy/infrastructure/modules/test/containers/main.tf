terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
  backend "s3" {
    bucket         = "noq-terraform-state"
    key            = "terraform_test/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "noq_terraform_state"
  }

}

provider "aws" {
  profile = var.profile
  region  = var.region
}

resource "aws_ecs_task_definition" "test_task_definition" {
  family                   = "${var.ecs_cluster_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  container_definitions    = <<DEFINITION
    [
      {
        "name": "${var.ecs_cluster_name}-api",
        "image": "259868150464.dkr.ecr.${var.region}.amazonaws.com/${var.stage}-registry-api:${var.stage}",
        "cpu": 1,
        "memory": 2048,
        "essential": true,
        "portMappings": [
          {
            "containerPort": 8092,
            "hostPort": 8092
          }
        ],
        "logging": {
          "driver": "awslogs",
          "options": {
            "awslogs-group": "${var.ecs_cluster_name}",
            "awslogs-region": "${var.region}",
            "awslogs-stream-prefix": "api"
          }
        }
      },
      {
        "name": "${var.ecs_cluster_name}-celery",
        "image": "259868150464.dkr.ecr.${var.region}.amazonaws.com/${var.stage}-registry-celery:${var.stage}",
        "cpu": 1,
        "memory": 2048,
        "essential": true,
        "logging": {                                                                                                                                                                                                                                        
          "driver": "awslogs",
          "options": {
            "awslogs-group": "${var.ecs_cluster_name}",
            "awslogs-region": "${var.region}",
            "awslogs-stream-prefix": "celery"
          }
        }
      }
    ]
    DEFINITION

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }  
  
  execution_role_arn = var.ecs_task_execution_role_arn
  task_role_arn = var.ecs_task_role_arn
}
  
resource "aws_ecs_service" "test_service" {
  name            = "${var.ecs_cluster_name}-test"

  cluster         = var.ecs_cluster_name
  desired_count   = 1
  enable_execute_command = true
  launch_type = "FARGATE"
  network_configuration {
    subnets = var.subnets
  }
  task_definition = aws_ecs_task_definition.test_task_definition.arn
}