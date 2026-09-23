# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------
variable "project_name" {
  description = "Short name used as a prefix for every resource."
  type        = string
  default     = "legal-rag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.project_name))
    error_message = "project_name must be 3-21 chars of lowercase letters, digits and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)."
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region. Also injected into the container as AWS_REGION (Bedrock + S3 client region)."
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Extra tags applied to every resource."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------------------
# Network (bring your own VPC)
# ------------------------------------------------------------------------------
variable "vpc_id" {
  description = "Existing VPC ID."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnets (at least two AZs) for the internet-facing ALB."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "An ALB requires at least two public subnets in different AZs."
  }
}

variable "private_subnet_ids" {
  description = "Private subnets (at least two AZs) for ECS tasks and RDS. They need egress to AWS APIs (NAT gateway or VPC endpoints for ECR, S3, Secrets Manager, CloudWatch Logs and Bedrock)."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "RDS subnet groups require at least two private subnets in different AZs."
  }
}

variable "allowed_ingress_cidrs" {
  description = "CIDR blocks allowed to reach the ALB on 443 (and 80, which only redirects to 443)."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# ------------------------------------------------------------------------------
# Load balancer / TLS
# ------------------------------------------------------------------------------
variable "acm_certificate_arn" {
  description = "ARN of an ISSUED ACM certificate for the HTTPS listener."
  type        = string
}

variable "alb_idle_timeout_seconds" {
  description = "ALB idle timeout. Must exceed the app REQUEST_TIMEOUT_SECONDS (180s) because self-correcting RAG calls are slow."
  type        = number
  default     = 300
}

variable "alb_deletion_protection" {
  description = "Protect the ALB from accidental deletion."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------------------
# Container / ECS
# ------------------------------------------------------------------------------
variable "image_tag" {
  description = "Immutable image tag pushed to ECR (e.g. the git SHA)."
  type        = string
  default     = "1.0.0"
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Initial number of tasks (autoscaling takes over afterwards when enabled)."
  type        = number
  default     = 2
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention."
  type        = number
  default     = 30
}

variable "log_level" {
  description = "Application LOG_LEVEL."
  type        = string
  default     = "INFO"
}

variable "enable_autoscaling" {
  description = "Enable target-tracking autoscaling on average CPU."
  type        = bool
  default     = true
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks when autoscaling is enabled."
  type        = number
  default     = 2
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks when autoscaling is enabled."
  type        = number
  default     = 6
}

variable "autoscaling_cpu_target" {
  description = "Target average CPU utilization (%)."
  type        = number
  default     = 60
}

# ------------------------------------------------------------------------------
# LLM (Amazon Bedrock)
# ------------------------------------------------------------------------------
variable "bedrock_llm_model_id" {
  description = "BEDROCK_LLM_MODEL_ID. A foundation model ID, or a cross-region inference profile ID (prefixed with us./eu./apac./global.). Verify availability in your region."
  type        = string
  default     = "anthropic.claude-opus-5"
}

variable "bedrock_embed_model_id" {
  description = "BEDROCK_EMBED_MODEL_ID."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

# ------------------------------------------------------------------------------
# Observability
# ------------------------------------------------------------------------------
variable "otel_enabled" {
  description = "OTEL_ENABLED. When true, an AWS Distro for OpenTelemetry (ADOT) sidecar is added and traces are exported to AWS X-Ray."
  type        = bool
  default     = false
}

variable "adot_collector_image" {
  description = "ADOT collector image used as the tracing sidecar. Pin a specific version in production."
  type        = string
  default     = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
}

# ------------------------------------------------------------------------------
# Database (RDS PostgreSQL + pgvector)
# ------------------------------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "db_engine_version" {
  description = "PostgreSQL major version (pgvector is available on RDS PostgreSQL 16)."
  type        = string
  default     = "16"
}

variable "db_allocated_storage_gb" {
  description = "Initial storage (GiB)."
  type        = number
  default     = 20
}

variable "db_max_allocated_storage_gb" {
  description = "Storage autoscaling ceiling (GiB)."
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "rag"
}

variable "db_master_username" {
  description = "Master username. The password is generated and rotated by RDS in Secrets Manager (manage_master_user_password)."
  type        = string
  default     = "rag_admin"
}

variable "db_multi_az" {
  description = "Deploy RDS in Multi-AZ mode."
  type        = bool
  default     = true
}

variable "db_backup_retention_days" {
  description = "Automated backup retention."
  type        = number
  default     = 7
}

variable "db_deletion_protection" {
  description = "Protect the database from deletion."
  type        = bool
  default     = true
}

# ------------------------------------------------------------------------------
# Dead-letter queue (S3)
# ------------------------------------------------------------------------------
variable "dlq_bucket_name" {
  description = "Globally unique bucket name for hallucination incidents. Defaults to <project>-<env>-dlq-<account_id>."
  type        = string
  default     = null
}

variable "dlq_glacier_transition_days" {
  description = "Days before incident objects transition to S3 Glacier Flexible Retrieval."
  type        = number
  default     = 90
}

# ------------------------------------------------------------------------------
# Secrets
# ------------------------------------------------------------------------------
variable "secret_recovery_window_days" {
  description = "Secrets Manager recovery window when a secret is deleted."
  type        = number
  default     = 7
}
