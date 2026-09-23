# AWS deployment (Terraform)

> **Cost warning: this configuration has never been applied.** It is written and
> statically validated (`terraform validate`, `terraform fmt -check`) in CI only.
> Running `terraform apply` creates **billable resources** (ALB, Fargate tasks,
> Multi-AZ RDS, Bedrock usage, CloudWatch, S3).

## What it creates

| Component | Resources |
|---|---|
| Image registry | ECR repository (scan on push, immutable tags, lifecycle policy) |
| Compute | ECS cluster (Container Insights), Fargate task definition, ECS service with deployment circuit breaker + rollback, optional CPU target-tracking autoscaling |
| Ingress | Internet-facing ALB, HTTPS listener (TLS 1.3 policy, ACM certificate), HTTP -> HTTPS 301 redirect, target group health-checking `/ready` |
| Network security | Security groups chained ALB (443/80) -> tasks (8000) -> RDS (5432) |
| Vector store | RDS PostgreSQL 16 (encrypted gp3, private, `publicly_accessible = false`, TLS enforced, master password managed and rotated by RDS in Secrets Manager) |
| Dead-letter queue | S3 bucket (versioning, SSE-S3, public access block, TLS-only bucket policy, Glacier after 90 days) |
| Secrets | Secrets Manager secrets for `API_KEY` and `PGVECTOR_DSN` (containers only, values set out-of-band) |
| Identity | Task **execution** role (ECR pull, logs, secret injection) and task role (Bedrock invoke on the configured models, `s3:PutObject` on `incidents/*`) |
| Logs / traces | CloudWatch log group (JSON logs); optional ADOT sidecar exporting OpenTelemetry traces to X-Ray |

The network is **bring-your-own**: pass `vpc_id`, `public_subnet_ids` (ALB) and
`private_subnet_ids` (tasks + RDS). Private subnets need egress to AWS APIs through a
NAT gateway or VPC endpoints (ECR api/dkr, S3 gateway, Secrets Manager, CloudWatch Logs,
Bedrock Runtime).

## How it maps to the application settings

The container image is the same one used locally; only environment variables change
(`src/legal_rag/config.py`).

| Env var | Value on AWS | Source |
|---|---|---|
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `bedrock` | task definition `environment` |
| `BEDROCK_LLM_MODEL_ID` / `BEDROCK_EMBED_MODEL_ID` | `var.bedrock_*_model_id` | task definition `environment` |
| `AWS_REGION` | `var.aws_region` | task definition `environment` |
| `VECTOR_STORE` | `pgvector` | task definition `environment` |
| `PGVECTOR_DSN` | DSN of the `rag_app` DB role | **Secrets Manager** via task definition `secrets` |
| `DLQ_BACKEND` / `DLQ_S3_BUCKET` | `s3` / created bucket | task definition `environment` |
| `API_KEY` | random key | **Secrets Manager** via task definition `secrets` |
| `LOG_FORMAT` | `json` | task definition `environment` |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | `var.otel_enabled` / `http://localhost:4318` (ADOT sidecar) | task definition `environment` |

AWS credentials are never configured in the container: boto3 picks up the task role
automatically.

Health checks: the container health check calls `/health` (liveness); the ALB target
group calls `/ready`, so a task only receives traffic once its dependencies are reachable.
The ALB idle timeout (300 s) is above the app request timeout (180 s).

## Usage (for reference only)

```bash
cp terraform.tfvars.example terraform.tfvars   # fill in VPC, subnets, certificate
terraform init
terraform plan                                  # requires AWS credentials
# terraform apply                               # creates billable resources

# After apply: push the image, set the secret values, enable pgvector
docker build -f docker/Dockerfile -t <ecr_repository_url>:<image_tag> .
aws secretsmanager put-secret-value --secret-id <api_key_secret_arn> --secret-string "<key>"
aws secretsmanager put-secret-value --secret-id <pgvector_dsn_secret_arn> --secret-string "postgresql+psycopg://rag_app:<pwd>@<rds_endpoint>/rag?sslmode=require"
# psql as the master user (credentials in rds_master_user_secret_arn): CREATE EXTENSION vector; (see rds.tf)
```

## Static validation (no credentials, no cost)

```bash
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 init -backend=false
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 validate
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 fmt -check -recursive
```
