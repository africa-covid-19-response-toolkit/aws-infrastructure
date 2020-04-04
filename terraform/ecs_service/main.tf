provider "aws" {
  region = var.region
}

terraform {
  backend "s3" {
    bucket = "et-covid-19-terraform-states"
    key    = "ecs"
    region = "us-east-1"
  }
}

variable "project" {
  default = "default"
}

variable "region" {
  default = "us-east-1"
}
variable "service_name" {}

variable "github_url" {}

variable "branch" {}

variable "envs" {
}

variable "secrets" {
}

variable "health_url" {
  default = "/health"
}

variable "cpu" {
  default = 128
}

variable "memory" {
  default = 256
}

variable "port" {
  default = 9000
}

variable "public" {
  default = true
}

variable "fargate" {
  default = false
}

locals {
  env          = terraform.workspace
  asg_name     = "${var.project}-asg-${local.env}"
  cluster_name = "${local.asg_name}-cluster"
  azs = [
    "us-east-1a",
    "us-east-1b",
  "us-east-1c"]
}

data "aws_iam_role" "ecs_task" {
  name = "${var.project}_ecs_task"
}
data "aws_iam_role" "builder" {
  name = "${var.project}_builder"
}

resource "aws_codebuild_project" "builder" {
  name        = "${var.service_name}-builder"
  description = "Builds ${var.github_url}"

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:2.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_REGION"
      value = "us-east-1"
    }
    environment_variable {
      name  = "IMAGE_REPO"
      value = aws_ecr_repository.ecr.repository_url
    }
    environment_variable {
      name  = "ECS_CLUSTER_NAME"
      value = data.aws_ecs_cluster.cluster.cluster_name
    }
    environment_variable {
      name  = "SERVICE_NAME"
      value = aws_ecs_service.service.name
    }
  }

  source {
    type            = "GITHUB"
    location        = var.github_url
    git_clone_depth = 1
  }

  source_version = var.branch

  service_role = data.aws_iam_role.builder.arn

  tags = {
    Environment = local.env
    Project     = var.project
    Service     = var.service_name
  }
}

resource "aws_ecr_repository" "ecr" {
  name                 = var.service_name
  image_tag_mutability = "MUTABLE"
}

data "aws_lb" "lb" {
  name = "${var.project}-${local.env}-lb"
}

data "aws_lb_listener" "http" {
  load_balancer_arn = data.aws_lb.lb.arn
  port              = "80"
}

data "aws_lb_listener" "https" {
  load_balancer_arn = data.aws_lb.lb.arn
  port              = "443"
}

resource "aws_lb_listener_rule" "http_route" {
  count        = var.public == true ? 0 : 1
  listener_arn = data.aws_lb_listener.http.arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }

  condition {
    host_header {
      values = [
      "${var.service_name}.**"]
    }
  }
}

resource "aws_lb_listener_rule" "https_route" {
  listener_arn = data.aws_lb_listener.https.arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }

  condition {
    host_header {
      values = [
      "${var.service_name}.**"]
    }
  }
}

data "aws_vpc" "vpc" {
  filter {
    name = "tag:Project"
    values = [
    var.project]
  }
}


resource "aws_lb_target_group" "tg" {
  name        = "${var.project}-${var.service_name}"
  port        = var.port
  target_type = "instance"
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.vpc.id

  health_check {
    interval = 30
    path     = var.health_url
  }
}

data "aws_ecs_cluster" "cluster" {
  cluster_name = local.cluster_name
}

data "aws_subnet_ids" "subnets" {
  vpc_id = data.aws_vpc.vpc.id
  filter {
    name = "tag:Private"
    values = [
      "false"
    ]
  }
}

resource "aws_cloudwatch_log_group" "yada" {
  name = "/${var.project}/${var.service_name}/ecs/task"


  tags = {
    Environment = local.env
    Project     = var.project
    Service     = var.service_name
  }
}

resource "aws_ecs_service" "service" {
  name            = var.service_name
  cluster         = data.aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = 1
  #  iam_role        = aws_iam_role.temeker_bot_role.arn

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = var.service_name
    container_port   = var.port
  }
}

resource "aws_ecs_task_definition" "task" {
  family = var.service_name
  container_definitions = templatefile("task-definition.json", {
    port         = var.port
    region       = "us-east-1"
    image        =  "${aws_ecr_repository.ecr.repository_url}:prod"
    secrets      = jsonencode(var.secrets)
    envs         = jsonencode(var.envs)
    log_group    = "/${var.project}/${var.service_name}/ecs/task"
    service_name = var.service_name
    memory       = var.memory
    cpu          = var.cpu
  })
  memory                   = var.memory
  cpu                      = var.cpu
  task_role_arn            = data.aws_iam_role.ecs_task.arn
  execution_role_arn       = data.aws_iam_role.ecs_task.arn
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]

  # volume {
  #   name      = "service-storage"
  #   host_path = "/ecs/service-storage"
  # }
}
