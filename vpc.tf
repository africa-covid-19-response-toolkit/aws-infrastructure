provider "aws" {
  region = "us-east-1"
}


variable "project" {
  default = "default"
}
variable "resource_prefix" {
  default = ""
}

locals {
  env          = terraform.workspace
  asg_name     = "${var.resource_prefix}asg-${local.env}"
  cluster_name = "${local.asg_name}-cluster"
  azs          = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "subnet_initial" {
  default = "10.2"
}
variable "machine_type" {
  default = "t2.micro"
}

variable "min_count" {
  default = 0
}

variable "max_count" {
  default = 3
}

variable "desired_count" {
  default = 0
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "vpc-${local.env}"
  cidr = "${var.subnet_initial}.0.0/16"

  azs             = local.azs
  private_subnets = ["${var.subnet_initial}.1.0/24", "${var.subnet_initial}.2.0/24", "${var.subnet_initial}.3.0/24"]
  public_subnets  = ["${var.subnet_initial}.101.0/24", "${var.subnet_initial}.102.0/24", "${var.subnet_initial}.103.0/24"]

  enable_nat_gateway = false
  enable_vpn_gateway = false

  private_subnet_tags = {
    Private = "true"
  }
  public_subnet_tags = {
    Private = "false"
  }

  tags = {
    Terraform   = "true"
    Project     = var.project
    Environment = local.env
  }
}

resource "aws_launch_template" "lunch_template" {
  name_prefix   = "${local.env}-template-"
  image_id      = "ami-04ac550b78324f651"
  instance_type = var.machine_type

  user_data = base64encode(templatefile("userdata.sh", {
    cluster_name = local.cluster_name
  }))
}

resource "aws_autoscaling_group" "asg" {
  name                = local.asg_name
  availability_zones  = local.azs
  desired_capacity    = var.desired_count
  max_size            = var.max_count
  min_size            = var.min_count
  vpc_zone_identifier = module.vpc.public_subnets[*]

  launch_template {
    id      = aws_launch_template.lunch_template.id
    version = "$Latest"
  }
}

resource "aws_ecs_capacity_provider" "cluster_cp" {
  name = "${var.resource_prefix}cp-asg-${local.asg_name}"

  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.asg.arn

    managed_scaling {
      status          = "ENABLED"
      target_capacity = 80
    }
  }
}

resource "aws_ecs_cluster" "cluster" {
  name               = local.cluster_name
  capacity_providers = ["FARGATE", aws_ecs_capacity_provider.cluster_cp.name]
  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.cluster_cp.name
    weight            = 1
  }

}

resource "aws_lb" "alb" {
  name               = "${var.resource_prefix}${local.env}-lb"
  internal           = false
  load_balancer_type = "application"
  subnets            = module.vpc.public_subnets[*]
}

resource "aws_lb_listener" "http" {
  name              = "${var.resource_prefix}${local.env}-http"
  load_balancer_arn = aws_lb.lb.arn
  port              = "80"
  protocol          = "HTTP"
}

# resource "aws_lb_listener" "https" {
#   name = "${var.resource_prefix}${local.env}-https"
#   load_balancer_arn = aws_lb.lb.arn
#   port              = "443"
#   protocol          = "HTTPS"
# }
