variable "region" {}
variable "cluster_id" {}
variable "instance_prefix" {}
variable "instance_type" {}
variable "instance_count" {}
variable "secrets" {}

locals {
  env = terraform.workspace
  azs = [
    "${var.region}a",
    "${var.region}b",
    "${var.region}c"]
}

resource "aws_docdb_cluster" "default" {
  cluster_identifier = "${var.cluster_id}"
  availability_zones = local.azs
  master_username    = "test"
  master_password    = "testasdfj2342"
}

resource "aws_docdb_cluster_instance" "cluster_instances" {
  count              = "${var.instance_count}"
  identifier         = "${var.instance_prefix}-${count.index}"
  cluster_identifier = "${aws_docdb_cluster.default.id}"
  instance_class     = "${var.instance_type}"
}


