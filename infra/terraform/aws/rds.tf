# RDS PostgreSQL 16 for the pgvector Gold layer (VECTOR_STORE=pgvector).
#
# pgvector ships with RDS PostgreSQL; it only needs to be enabled once per database
# by a privileged user (this is a SQL step, not an infrastructure one):
#
#   CREATE EXTENSION IF NOT EXISTS vector;
#   CREATE ROLE rag_app LOGIN PASSWORD '<password>';
#   GRANT CONNECT ON DATABASE rag TO rag_app;
#   GRANT USAGE, CREATE ON SCHEMA public TO rag_app;
#
# The master password is generated, stored and rotated by RDS in Secrets Manager
# (manage_master_user_password = true); it never appears in code or state.

resource "aws_db_subnet_group" "this" {
  name        = "${local.name}-db"
  description = "Private subnets for the legal-rag database"
  subnet_ids  = var.private_subnet_ids
}

resource "aws_db_parameter_group" "this" {
  name        = "${local.name}-pg16"
  family      = "postgres16"
  description = "legal-rag PostgreSQL 16 parameters"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
}

resource "aws_db_instance" "this" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  db_name                     = var.db_name
  username                    = var.db_master_username
  manage_master_user_password = true

  allocated_storage     = var.db_allocated_storage_gb
  max_allocated_storage = var.db_max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.this.name
  publicly_accessible    = false
  multi_az               = var.db_multi_az
  port                   = 5432

  iam_database_authentication_enabled = true
  auto_minor_version_upgrade          = true
  backup_retention_period             = var.db_backup_retention_days
  copy_tags_to_snapshot               = true
  deletion_protection                 = var.db_deletion_protection
  skip_final_snapshot                 = false
  final_snapshot_identifier           = "${local.name}-db-final"
  performance_insights_enabled        = true
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]
}
