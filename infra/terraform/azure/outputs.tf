output "resource_group_name" {
  description = "Resource group containing every resource."
  value       = azurerm_resource_group.this.name
}

output "container_app_url" {
  description = "Public HTTPS URL of the API (managed TLS certificate on *.azurecontainerapps.io)."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "Push the image built from docker/Dockerfile here as <image_name>:<image_tag>."
  value       = azurerm_container_registry.this.login_server
}

output "key_vault_name" {
  description = "Key Vault holding the app secrets (set api-key and pgvector-dsn here)."
  value       = azurerm_key_vault.this.name
}

output "postgres_fqdn" {
  description = "Private FQDN of the PostgreSQL Flexible Server (resolvable only inside the VNet)."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "openai_endpoint" {
  description = "AZURE_OPENAI_ENDPOINT."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "storage_account_name" {
  description = "Storage account hosting the DLQ container."
  value       = azurerm_storage_account.dlq.name
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace receiving the container's JSON logs."
  value       = azurerm_log_analytics_workspace.this.id
}

output "managed_identity_client_id" {
  description = "Client ID of the app's user-assigned managed identity."
  value       = azurerm_user_assigned_identity.app.client_id
}
