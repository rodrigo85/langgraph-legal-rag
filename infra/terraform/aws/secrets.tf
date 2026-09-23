# Secret containers only: NO secret values live in this code or in Terraform state.
# Populate them out-of-band after the first apply, e.g.:
#
#   aws secretsmanager put-secret-value --secret-id <api_key_secret_arn> --secret-string "<random-key>"
#   aws secretsmanager put-secret-value --secret-id <pgvector_dsn_secret_arn> \
#     --secret-string "postgresql+psycopg://rag_app:<password>@<rds_endpoint>:5432/rag?sslmode=require"
#
# The DSN should use a dedicated least-privilege application role (rag_app), not the
# RDS master user whose password RDS rotates in its own managed secret.
# ECS injects both values as environment variables through the task definition
# `secrets` block, so the application never calls Secrets Manager itself.

resource "aws_secretsmanager_secret" "api_key" {
  name                    = "${local.name}/api-key"
  description             = "API_KEY required in the X-API-Key header of the legal-rag API"
  recovery_window_in_days = var.secret_recovery_window_days
}

resource "aws_secretsmanager_secret" "pgvector_dsn" {
  name                    = "${local.name}/pgvector-dsn"
  description             = "PGVECTOR_DSN (SQLAlchemy URL) for the pgvector Gold layer"
  recovery_window_in_days = var.secret_recovery_window_days
}
