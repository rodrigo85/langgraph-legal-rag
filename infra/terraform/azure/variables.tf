# ------------------------------------------------------------------------------
# General
# ------------------------------------------------------------------------------
variable "subscription_id" {
  description = "Target Azure subscription ID. Leave null to use ARM_SUBSCRIPTION_ID."
  type        = string
  default     = null
}

variable "project_name" {
  description = "Short name used as a prefix for every resource."
  type        = string
  default     = "legal-rag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,14}$", var.project_name))
    error_message = "project_name must be 3-15 chars of lowercase letters, digits and hyphens (Azure name limits)."
  }
}

variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)."
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Azure region. Must offer Azure OpenAI with the selected models."
  type        = string
  default     = "eastus2"
}

variable "tags" {
  description = "Extra tags applied to every resource."
  type        = map(string)
  default     = {}
}

# ------------------------------------------------------------------------------
# Network
# ------------------------------------------------------------------------------
variable "vnet_address_space" {
  description = "Address space of the VNet hosting Container Apps and PostgreSQL."
  type        = string
  default     = "10.40.0.0/16"
}

variable "container_apps_subnet_cidr" {
  description = "Subnet delegated to the Container Apps environment (minimum /27 for workload-profile environments)."
  type        = string
  default     = "10.40.0.0/23"
}

variable "postgres_subnet_cidr" {
  description = "Subnet delegated to PostgreSQL Flexible Server (private access, no public endpoint)."
  type        = string
  default     = "10.40.2.0/24"
}

# ------------------------------------------------------------------------------
# Container App
# ------------------------------------------------------------------------------
variable "image_name" {
  description = "Repository name inside the Azure Container Registry."
  type        = string
  default     = "legal-rag"
}

variable "image_tag" {
  description = "Image tag pushed to ACR (e.g. the git SHA). The image must exist before the Container App is created."
  type        = string
  default     = "1.0.0"
}

variable "acr_sku" {
  description = "Azure Container Registry SKU (Premium is required for private endpoints and geo-replication)."
  type        = string
  default     = "Standard"
}

variable "container_cpu" {
  description = "vCPU per replica (Consumption profile valid combinations: 0.5/1Gi, 1/2Gi, 2/4Gi...)."
  type        = number
  default     = 1
}

variable "container_memory" {
  description = "Memory per replica."
  type        = string
  default     = "2Gi"
}

variable "min_replicas" {
  description = "Minimum replicas (keep >= 1 to avoid cold starts on a latency-sensitive API)."
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum replicas."
  type        = number
  default     = 5
}

variable "http_concurrent_requests_per_replica" {
  description = "HTTP scale rule: concurrent requests per replica before scaling out."
  type        = number
  default     = 10
}

variable "log_level" {
  description = "Application LOG_LEVEL."
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "Log Analytics retention."
  type        = number
  default     = 30
}

variable "otel_enabled" {
  description = "OTEL_ENABLED for the application."
  type        = bool
  default     = false
}

variable "otel_exporter_otlp_endpoint" {
  description = "OTEL_EXPORTER_OTLP_ENDPOINT, e.g. an OpenTelemetry Collector that forwards to Azure Monitor / Application Insights."
  type        = string
  default     = "http://localhost:4318"
}

# ------------------------------------------------------------------------------
# Azure OpenAI
# ------------------------------------------------------------------------------
variable "openai_api_version" {
  description = "AZURE_OPENAI_API_VERSION used by the app."
  type        = string
  default     = "2024-10-21"
}

variable "openai_chat_deployment_name" {
  description = "AZURE_OPENAI_CHAT_DEPLOYMENT (deployment name, not model name)."
  type        = string
  default     = "gpt-4o-mini"
}

variable "openai_chat_model" {
  description = "Chat model name and version to deploy."
  type = object({
    name    = string
    version = string
  })
  default = {
    name    = "gpt-4o-mini"
    version = "2024-07-18"
  }
}

variable "openai_chat_capacity" {
  description = "Chat deployment capacity in thousands of tokens per minute."
  type        = number
  default     = 30
}

variable "openai_embed_deployment_name" {
  description = "AZURE_OPENAI_EMBED_DEPLOYMENT (deployment name, not model name)."
  type        = string
  default     = "text-embedding-3-small"
}

variable "openai_embed_model" {
  description = "Embedding model name and version to deploy."
  type = object({
    name    = string
    version = string
  })
  default = {
    name    = "text-embedding-3-small"
    version = "1"
  }
}

variable "openai_embed_capacity" {
  description = "Embedding deployment capacity in thousands of tokens per minute."
  type        = number
  default     = 30
}

variable "openai_deployment_sku" {
  description = "Deployment SKU (Standard = regional data processing, GlobalStandard = global routing)."
  type        = string
  default     = "Standard"
}

# ------------------------------------------------------------------------------
# PostgreSQL Flexible Server (pgvector)
# ------------------------------------------------------------------------------
variable "postgres_sku_name" {
  description = "PostgreSQL Flexible Server SKU."
  type        = string
  default     = "GP_Standard_D2ds_v5"
}

variable "postgres_storage_mb" {
  description = "Storage size in MB."
  type        = number
  default     = 32768
}

variable "postgres_admin_login" {
  description = "Administrator login. The password is generated and stored in Key Vault."
  type        = string
  default     = "rag_admin"
}

variable "postgres_database_name" {
  description = "Application database."
  type        = string
  default     = "rag"
}

variable "postgres_backup_retention_days" {
  description = "Backup retention (7-35 days)."
  type        = number
  default     = 7
}

variable "postgres_high_availability" {
  description = "Enable zone-redundant high availability."
  type        = bool
  default     = false
}

# ------------------------------------------------------------------------------
# Storage (DLQ)
# ------------------------------------------------------------------------------
variable "dlq_container_name" {
  description = "DLQ_AZURE_CONTAINER."
  type        = string
  default     = "legal-rag-dlq"
}

variable "dlq_cool_tier_after_days" {
  description = "Move incident blobs to the Cool tier after N days."
  type        = number
  default     = 30
}

variable "dlq_archive_tier_after_days" {
  description = "Move incident blobs to the Archive tier after N days."
  type        = number
  default     = 90
}
