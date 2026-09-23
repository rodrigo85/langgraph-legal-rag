# Azure deployment (Terraform)

> **Cost warning: this configuration has never been applied.** It is written and
> statically validated (`terraform validate`, `terraform fmt -check`) in CI only.
> Running `terraform apply` creates **billable resources** (Container Apps,
> PostgreSQL Flexible Server, Azure OpenAI usage, Log Analytics, Storage, ACR).

## What it creates

| Component | Resources |
|---|---|
| Foundation | Resource group, Log Analytics workspace, user-assigned managed identity |
| Network | VNet with a subnet delegated to Container Apps and a subnet delegated to PostgreSQL, private DNS zone |
| Image registry | Azure Container Registry (admin user disabled, pulls via managed identity) |
| Compute | Container Apps environment (VNet-integrated, zone-redundant) + Container App: external HTTPS ingress to port 8000, startup/liveness probes on `/health`, readiness probe on `/ready`, min/max replicas with an HTTP concurrency scale rule |
| Vector store | PostgreSQL Flexible Server 16, private access only (no public endpoint), `azure.extensions = VECTOR`, TLS required |
| Dead-letter queue | Storage account (TLS 1.2 minimum, HTTPS only, no public blob access, versioning, soft delete) + private container, lifecycle to Cool (30 d) and Archive (90 d) |
| LLM | Azure OpenAI account + two deployments (chat and embeddings; names are variables) |
| Secrets | Key Vault in RBAC mode, purge protection; secrets referenced by the Container App through the managed identity |
| Identity | Role assignments for the managed identity: AcrPull (ACR), Key Vault Secrets User (vault), Storage Blob Data Contributor (DLQ container only), Cognitive Services OpenAI User (OpenAI account) |

## How it maps to the application settings

The container image is the same one used locally; only environment variables change
(`src/legal_rag/config.py`).

| Env var | Value on Azure | Source |
|---|---|---|
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `azure_openai` | Container App `env` |
| `AZURE_OPENAI_ENDPOINT` | OpenAI account endpoint | Container App `env` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` / `AZURE_OPENAI_EMBED_DEPLOYMENT` | deployment names | Container App `env` |
| `AZURE_OPENAI_API_KEY` | account key | **Key Vault** reference (`azure-openai-api-key`) |
| `VECTOR_STORE` | `pgvector` | Container App `env` |
| `PGVECTOR_DSN` | DSN of the `rag_app` DB role | **Key Vault** reference (`pgvector-dsn`, set out-of-band) |
| `DLQ_BACKEND` / `DLQ_AZURE_CONTAINER` | `azure_blob` / DLQ container | Container App `env` |
| `AZURE_STORAGE_CONNECTION_STRING` | storage connection string | **Key Vault** reference (`azure-storage-connection-string`) |
| `API_KEY` | random key | **Key Vault** reference (`api-key`, set out-of-band) |
| `LOG_FORMAT` | `json` (collected by Log Analytics) | Container App `env` |
| `OTEL_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | variables | Container App `env` |

`api-key` and `pgvector-dsn` are created as placeholders with `ignore_changes = [value]`,
so their real values are never in code or state. The OpenAI key and storage connection
string are copied into Key Vault from resources Terraform already manages (they are in
state regardless), and the PostgreSQL admin password is generated with `random_password`
and stored in Key Vault. Use an encrypted remote backend for state.

**Keyless next step:** the app currently authenticates to Azure OpenAI and Blob Storage
with a key / connection string. The managed identity already holds the
`Cognitive Services OpenAI User` and `Storage Blob Data Contributor` roles, so switching
the SDK clients to `DefaultAzureCredential` would allow `local_auth_enabled = false` on
OpenAI and `shared_access_key_enabled = false` on Storage.

## Usage (for reference only)

```bash
cp terraform.tfvars.example terraform.tfvars   # fill in subscription and names
terraform init
terraform plan                                  # requires Azure credentials
# terraform apply                               # creates billable resources

# The Container App needs the image to exist: create the ACR first, push, then apply the rest
terraform apply -target=azurerm_container_registry.this
az acr build -r <acr_name> -f docker/Dockerfile -t legal-rag:<image_tag> .
az keyvault secret set --vault-name <key_vault_name> --name api-key --value "<key>"
az keyvault secret set --vault-name <key_vault_name> --name pgvector-dsn --value "postgresql+psycopg://rag_app:<pwd>@<postgres_fqdn>:5432/rag?sslmode=require"
# From inside the VNet (e.g. a Container Apps job): CREATE EXTENSION vector; (see postgres.tf)
```

## Static validation (no credentials, no cost)

```bash
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 init -backend=false
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 validate
docker run --rm -v "$PWD:/w" -w /w hashicorp/terraform:1.9 fmt -check -recursive
```
