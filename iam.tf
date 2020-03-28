resource "aws_iam_role_policy" "ecs_task_policy" {
  name = "${var.project}_ecs_task_policy"
  role = aws_iam_role.ecs_task_role.id

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }
EOF
}

data "aws_iam_policy_document" "ecs_task_role" {
  statement {
    sid     = "1"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com", "ecs.amazonaws.com"]
    }
    effect = "Allow"
  }
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.project}_ecs_task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_role.json
}

data "aws_iam_policy_document" "builder" {
  statement {
    sid     = "1"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
    effect = "Allow"
  }
}

resource "aws_iam_role_policy" "builder" {
  name = "${var.project}_builder_policy"
  role = aws_iam_role.builder.id

  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }
EOF
}

resource "aws_iam_role" "builder" {
  name               = "${var.project}_builder"
  assume_role_policy = data.aws_iam_policy_document.builder.json
}

