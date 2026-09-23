resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.name}"
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  infrastructure_subnet_id   = azurerm_subnet.container_apps.id
  zone_redundancy_enabled    = true

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  tags = local.tags

  # Azure creates this managed resource group automatically.
  lifecycle {
    ignore_changes = [infrastructure_resource_group_name]
  }
}

locals {
  # Key Vault secret -> Container App secret name -> environment variable.
  app_secrets = {
    "api-key"                         = { env = "API_KEY", id = azurerm_key_vault_secret.api_key.versionless_id }
    "pgvector-dsn"                    = { env = "PGVECTOR_DSN", id = azurerm_key_vault_secret.pgvector_dsn.versionless_id }
    "azure-openai-api-key"            = { env = "AZURE_OPENAI_API_KEY", id = azurerm_key_vault_secret.azure_openai_api_key.versionless_id }
    "azure-storage-connection-string" = { env = "AZURE_STORAGE_CONNECTION_STRING", id = azurerm_key_vault_secret.azure_storage_connection_string.versionless_id }
  }

  # Non-secret configuration, mapped 1:1 to legal_rag.config.Settings.
  app_environment = {
    LLM_PROVIDER                  = "azure_openai"
    EMBEDDING_PROVIDER            = "azure_openai"
    AZURE_OPENAI_ENDPOINT         = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_API_VERSION      = var.openai_api_version
    AZURE_OPENAI_CHAT_DEPLOYMENT  = azurerm_cognitive_deployment.chat.name
    AZURE_OPENAI_EMBED_DEPLOYMENT = azurerm_cognitive_deployment.embeddings.name
    VECTOR_STORE                  = "pgvector"
    DLQ_BACKEND                   = "azure_blob"
    DLQ_AZURE_CONTAINER           = azurerm_storage_container.dlq.name
    LOG_FORMAT                    = "json"
    LOG_LEVEL                     = var.log_level
    OTEL_ENABLED                  = tostring(var.otel_enabled)
    OTEL_EXPORTER_OTLP_ENDPOINT   = var.otel_exporter_otlp_endpoint
    OTEL_SERVICE_NAME             = local.name
  }
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${local.name}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  dynamic "secret" {
    for_each = local.app_secrets

    content {
      name                = secret.key
      key_vault_secret_id = secret.value.id
      identity            = azurerm_user_assigned_identity.app.id
    }
  }

  ingress {
    external_enabled           = true
    target_port                = local.container_port
    transport                  = "auto"
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = tostring(var.http_concurrent_requests_per_replica)
    }

    container {
      name   = "api"
      image  = "${azurerm_container_registry.this.login_server}/${var.image_name}:${var.image_tag}"
      cpu    = var.container_cpu
      memory = var.container_memory

      dynamic "env" {
        for_each = local.app_environment

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.app_secrets

        content {
          name        = env.value.env
          secret_name = env.key
        }
      }

      startup_probe {
        transport               = "HTTP"
        port                    = local.container_port
        path                    = "/health"
        interval_seconds        = 5
        failure_count_threshold = 30
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = local.container_port
        path                    = "/health"
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = local.container_port
        path                    = "/ready"
        interval_seconds        = 15
        timeout                 = 10
        failure_count_threshold = 3
        success_count_threshold = 1
      }
    }
  }

  tags = local.tags

  # The identity must be able to pull the image and read the secrets before the
  # first revision is created.
  depends_on = [
    azurerm_role_assignment.app_acr_pull,
    azurerm_role_assignment.app_kv_secrets_user,
  ]
}
