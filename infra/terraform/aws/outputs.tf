output "alb_dns_name" {
  description = "Public DNS name of the ALB. Point your domain (matching the ACM certificate) here with a CNAME/alias record."
  value       = aws_lb.this.dns_name
}

output "ecr_repository_url" {
  description = "Push the image built from docker/Dockerfile here, tagged with var.image_tag."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  description = "ECS service name."
  value       = aws_ecs_service.api.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group receiving the JSON application logs."
  value       = aws_cloudwatch_log_group.app.name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port) to build PGVECTOR_DSN."
  value       = aws_db_instance.this.endpoint
}

output "rds_master_user_secret_arn" {
  description = "ARN of the RDS-managed secret holding the master credentials (for the one-off pgvector bootstrap)."
  value       = try(aws_db_instance.this.master_user_secret[0].secret_arn, null)
}

output "dlq_bucket_name" {
  description = "S3 bucket used as DLQ_S3_BUCKET."
  value       = aws_s3_bucket.dlq.bucket
}

output "api_key_secret_arn" {
  description = "Secrets Manager secret to populate with API_KEY."
  value       = aws_secretsmanager_secret.api_key.arn
}

output "pgvector_dsn_secret_arn" {
  description = "Secrets Manager secret to populate with PGVECTOR_DSN."
  value       = aws_secretsmanager_secret.pgvector_dsn.arn
}

output "task_role_arn" {
  description = "IAM role assumed by the application code."
  value       = aws_iam_role.task.arn
}
