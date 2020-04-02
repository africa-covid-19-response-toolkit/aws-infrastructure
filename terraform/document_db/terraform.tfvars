cluster_id = "data-cluster"
instance_prefix = "instance"
instance_type = "db.r5.large"
instance_count= "1"
secrets = [{
    name      = "creds",
    valueFrom = "document-db/master_creds"
}]