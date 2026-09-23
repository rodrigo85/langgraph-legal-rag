# Key Vault in RBAC mode. The Container App reads these secrets through Key Vault
# references using the user-assigned identity; values are exposed to the container
# as environment variables, so the application never talks to Key Vault itself.

resource "azurerm_key_vault" "this" {
  name                       = substr("kv-${local.compact_name}-${local.suffix}", 0, 24)
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = local.tags
}

# The identity running Terraform needs data-plane rights to create the secrets below.
resource "azurerm_role_assignment" "deployer_kv_secrets_officer" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# --- Placeholders: real values are set out-of-band and never stored in code ----
#   az keyvault secret set --vault-name <kv> --name api-key      --value "<random-key>"
#   az keyvault secret set --vault-name <kv> --name pgvector-dsn \
#     --value "postgresql+psycopg://rag_app:<password>@<postgres_fqdn>:5432/rag?sslmode=require"
# ignore_changes keeps Terraform from overwriting them afterwards.

resource "azurerm_key_vault_secret" "api_key" {
  name         = "api-key"
  value        = "set-out-of-band"
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"

  lifecycle {
    ignore_changes = [value]
  }

  depends_on = [azurerm_role_assignment.deployer_kv_secrets_officer]
}

resource "azurerm_key_vault_secret" "pgvector_dsn" {
  name         = "pgvector-dsn"
  value        = "set-out-of-band"
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"

  lifecycle {
    ignore_changes = [value]
  }

  depends_on = [azurerm_role_assignment.deployer_kv_secrets_officer]
}

# --- Secrets derived from resources Terraform already manages ------------------
# These values are already present in Terraform state as resource attributes, so
# copying them into Key Vault adds no new exposure. Use an encrypted remote backend.

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "azure-openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"

  depends_on = [azurerm_role_assignment.deployer_kv_secrets_officer]
}

resource "azurerm_key_vault_secret" "azure_storage_connection_string" {
  name         = "azure-storage-connection-string"
  value        = azurerm_storage_account.dlq.primary_connection_string
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"

  depends_on = [azurerm_role_assignment.deployer_kv_secrets_officer]
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = "postgres-admin-password"
  value        = random_password.postgres_admin.result
  key_vault_id = azurerm_key_vault.this.id
  content_type = "text/plain"

  depends_on = [azurerm_role_assignment.deployer_kv_secrets_officer]
}
