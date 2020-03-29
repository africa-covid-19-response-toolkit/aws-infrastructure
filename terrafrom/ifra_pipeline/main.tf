provider "aws" {
  region = "us-east-1"
}
variable "project" {
  default = "default"
}
variable "service_name" {
  default = "infra"
}

variable "github_url" {
  default = "https://github.com/Ethiopia-COVID19/aws-infrastructure"
}


locals {
  env = terraform.workspace
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

    environment_variable {
      name  = "AWS_REGION"
      value = "us-east-1"
    }
  }

  source {
    type            = "GITHUB"
    location        = var.github_url
    git_clone_depth = 1
  }

  source_version = "master"

  service_role = data.aws_iam_role.builder.arn

  tags = {
    Environment = local.env
    Project     = var.project
    Service     = var.service_name
  }
}

