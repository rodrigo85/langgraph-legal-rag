# Infrastructure as Code

Production-grade Terraform for **AWS** and **Azure**, written and statically validated
in CI (`terraform fmt -check`, `terraform init -backend=false`, `terraform validate`).

> **Not applied.** Nothing here has been deployed and no cloud credentials are used
> anywhere in this repository. Running `terraform apply` creates billable resources.

```
infra/
  terraform/
    aws/     ECS Fargate + ALB + RDS PostgreSQL (pgvector) + Bedrock + S3 + Secrets Manager
    azure/   Container Apps + PostgreSQL Flexible Server (pgvector) + Azure OpenAI + Blob + Key Vault
```

## Principle: the app code is identical, only environment variables change

The FastAPI service (`legal_rag.api.main:app`) reads everything from environment
variables (`src/legal_rag/config.py`). Each local-simulation component has a managed
counterpart selected purely by configuration:

| Local simulation | AWS | Azure | Switched by |
|---|---|---|---|
| FastAPI container (`docker/Dockerfile`) | ECS Fargate behind an ALB (image in ECR) | Azure Container Apps (image in ACR) | same image |
| Ollama (LLM + embeddings) | Amazon Bedrock | Azure OpenAI | `LLM_PROVIDER`, `EMBEDDING_PROVIDER` |
| pgvector container | RDS for PostgreSQL 16 + `vector` extension | Azure Database for PostgreSQL Flexible Server 16 + `VECTOR` extension | `VECTOR_STORE=pgvector`, `PGVECTOR_DSN` |
| LocalStack S3 (DLQ) | Amazon S3 | - | `DLQ_BACKEND=s3`, `DLQ_S3_BUCKET` |
| Azurite (DLQ) | - | Azure Blob Storage | `DLQ_BACKEND=azure_blob`, `DLQ_AZURE_CONTAINER` |
| Jaeger (OpenTelemetry traces) | ADOT collector sidecar -> AWS X-Ray, JSON logs in CloudWatch | OpenTelemetry collector -> Azure Monitor, JSON logs in Log Analytics | `OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `LOG_FORMAT=json` |
| `.env` file | AWS Secrets Manager (ECS task `secrets`) | Azure Key Vault (Container Apps Key Vault references) | platform injects env vars |
| Local credentials | IAM task role (no keys) | User-assigned managed identity | - |

Secrets are always injected by the platform as environment variables, so the
application never talks to a secret store directly and never contains
cloud-specific code paths beyond the provider adapters.

See [`terraform/aws/README.md`](terraform/aws/README.md) and
[`terraform/azure/README.md`](terraform/azure/README.md) for resources, variable
mapping and the (reference-only) deployment steps.
