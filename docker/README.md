# Docker: local production simulation

Everything the cloud deployment needs, running on one machine at zero cost. The
application container is the same image that Terraform deploys to ECS Fargate
(AWS) or Container Apps (Azure); only environment variables differ.

## Files

| File | Purpose |
| :--- | :--- |
| [`Dockerfile`](Dockerfile) | Multi-stage build: wheels compiled in a builder stage, slim runtime image, non-root user (`uid 10001`), `HEALTHCHECK` on `/health`, entrypoint `legal-rag-api` |
| [`../docker-compose.yml`](../docker-compose.yml) | The full local topology below, plus a one-off `indexer` job |
| [`localstack/init-s3.sh`](localstack/init-s3.sh) | Creates the DLQ bucket when LocalStack is ready (Terraform owns the bucket in the cloud) |
| [`../.dockerignore`](../.dockerignore) | Keeps `.venv`, `chroma_db`, raw PDFs, tests and infra out of the build context |

## Topology

| Service | Image | Port | Stands in for |
| :--- | :--- | :--- | :--- |
| `api` | `legal-rag:local` (built from `Dockerfile`) | 8000 | ECS Fargate task / Azure Container App |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | RDS PostgreSQL / PostgreSQL Flexible Server (Gold vector store) |
| `localstack` | `localstack/localstack:4.0` (S3 only) | 4566 | Amazon S3 (dead-letter queue) |
| `azurite` | `mcr.microsoft.com/azure-storage/azurite:3.34.0` | 10000 | Azure Blob Storage (dead-letter queue) |
| `jaeger` | `jaegertracing/all-in-one:1.62.0` | 16686 (UI), 4318 (OTLP) | ADOT → X-Ray / Azure Monitor (traces) |
| Ollama | runs on the **host GPU**, reached as `host.docker.internal:11434` | 11434 | Amazon Bedrock / Azure OpenAI |

The `api` container is configured (see the `x-app-env` anchor in the compose file) with
`VECTOR_STORE=pgvector`, `DLQ_BACKEND=s3` (default) or `azure_blob`, `LOG_FORMAT=json`,
`OTEL_ENABLED=true` and `API_KEY=local-dev-key`. LocalStack uses the dummy credentials
`test`/`test`; Azurite uses its well-known public development account. Neither is a secret.

## Commands

```bash
# 1. Start the infrastructure and the API (AWS-like: DLQ on S3)
docker compose up -d --build            # or: make up

# 2. Build the Gold layer inside pgvector (one-off job, reads ./data read-only; ~20 s for 1,081 chunks)
docker compose --profile jobs run --rm indexer    # or: make index

# 3. Probe and query
curl localhost:8000/health              # {"status":"ok"}
curl localhost:8000/ready               # {"status":"ready","vectors":1081}
curl -X POST localhost:8000/v1/query \
  -H "X-API-Key: local-dev-key" -H "X-Request-ID: demo-001" \
  -H "Content-Type: application/json" \
  -d '{"question": "O que Satya Nadella testemunhou sobre o Bing?"}'

# 4. Switch the DLQ to Azure Blob (Azurite) — everything else unchanged
DLQ_BACKEND=azure_blob docker compose up -d       # or: make up-azure

# 5. Inspect what was produced
docker compose exec localstack awslocal s3 ls s3://legal-rag-dlq --recursive   # rejected drafts on "S3"
open http://localhost:16686                                                    # Jaeger: one trace per request, span "graph.invoke"
docker compose logs -f api                                                     # JSON logs correlated by request_id

# 6. Stop (add -v to also drop the pgvector volume)
docker compose down                     # or: make down
```

## What was verified with this setup

- `indexer` job: 1,081 chunks embedded and stored in pgvector in 21 s.
- `POST /v1/query`: HTTP 200 in 18 s with `hallucination_verdict=grounded`, pages 115 and 255 cited; the same
  `request_id` appears in every node log line and in the Jaeger trace.
- Rejected drafts written to LocalStack S3 as `incidents/YYYY/MM/DD/<id>.json`, and, after switching the backend,
  to the Azurite container `legal-rag-dlq` (created lazily by the sink).
- A question the retriever could not support ended in abstention after 3 correction cycles instead of a hallucination.

## Notes

- Ollama is intentionally **not** containerised: GPU passthrough on Windows/Docker Desktop is unreliable, and in the
  cloud the LLM is a managed service anyway. `extra_hosts: host.docker.internal:host-gateway` makes the host reachable
  from Linux too.
- The `postgres` volume (`pgdata`) persists the index between restarts; `make index` is idempotent and skips
  re-embedding when the collection already has vectors.
- Chroma (`VECTOR_STORE=chroma`) is the default outside Docker for a zero-dependency developer loop; the compose stack
  deliberately uses pgvector to exercise the production path.
