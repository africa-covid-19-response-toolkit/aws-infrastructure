variable "region" {}
variable "cluster_id" {}
variable "instance_prefix" {}
variable "instance_type" {}
variable "instance_count" {}

locals {
  env = terraform.workspace
  azs = [
    "${var.region}a",
    "${var.region}b",
    "${var.region}c"]
}

data "aws_secretsmanager_secret_version" "creds" {
  secret_id = "document-db/master_creds"
}

resource "aws_docdb_cluster" "default" {
  cluster_identifier = "${var.cluster_id}"
  availability_zones = local.azs
  master_username    = jsondecode("${data.aws_secretsmanager_secret_version.creds.secret_string}")["username"]
  master_password    = jsondecode("${data.aws_secretsmanager_secret_version.creds.secret_string}")["password"]
}

resource "aws_docdb_cluster_instance" "cluster_instances" {
  count              = "${var.instance_count}"
  identifier         = "${var.instance_prefix}-${count.index}"
  cluster_identifier = "${aws_docdb_cluster.default.id}"
  instance_class     = "${var.instance_type}"
}