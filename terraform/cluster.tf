provider "aws" {
  region = var.region
}

terraform {
  backend "s3" {
    bucket = "et-covid-19-terraform-states"
    key = "cluster"
  }
}

variable "region" {}

variable "project" {
  default = "default"
}

variable "subnet_initial" {
  default = "10.2"
}
variable "machine_type" {
  default = "t2.micro"
}

variable "domain" {}

variable "min_count" {
  default = 0
}

variable "max_count" {
  default = 3
}

variable "desired_count" {
  default = 0
}

locals {
  env          = terraform.workspace
  asg_name     = "${var.project}-asg-${local.env}"
  cluster_name = "${local.asg_name}-cluster"
  azs = [
    "${var.region}a",
    "${var.region}b",
    "${var.region}c"]
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
  enable_dns_support = true
  enable_dns_hostnames =  true

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

resource "aws_iam_instance_profile" "profile" {
  role = aws_iam_role.instanace.name

}

resource "aws_launch_template" "lunch_template" {
  name_prefix   = "${local.env}-template-"
  image_id      = "ami-00f69adbdc780866c"
  instance_type = var.machine_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.profile.arn
  }

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

  lifecycle {
    ignore_changes = [
      desired_capacity]
  }
}

resource "aws_ecs_capacity_provider" "cluster_cp" {
  name = "${local.asg_name}-cp"

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

data "aws_route53_zone" "zone" {
  name = var.domain
}

resource "aws_route53_record" "hosted_zone" {
  allow_overwrite = true
  name = "*.${var.domain}"
  zone_id         = "${data.aws_route53_zone.zone.zone_id}"
  type            = "A"

  alias {
    name    = aws_lb.alb.dns_name
    zone_id = aws_lb.alb.zone_id

    evaluate_target_health = true
  }
}

resource "aws_lb" "alb" {
  name               = "${var.project}-${local.env}-lb"
  internal           = false
  load_balancer_type = "application"
  subnets            = module.vpc.public_subnets[*]
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "The listerer is up and running, we just need to make sure there are rules ;-)"
      status_code  = "200"
    }
  }
}

data "aws_acm_certificate" "cert" {
  domain   = "*.${var.domain}"
  statuses = ["ISSUED"]
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = data.aws_acm_certificate.cert.arn

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "The listerer is up and running, we just need to make sure there are rules ;-)"
      status_code  = "200"
    }
  }
}
