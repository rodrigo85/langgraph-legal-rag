data "azurerm_client_config" "current" {}

# Globally unique names (Key Vault, Storage, ACR, PostgreSQL, OpenAI subdomain)
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

locals {
  name         = "${var.project_name}-${var.environment}"
  compact_name = replace(local.name, "-", "")
  suffix       = random_string.suffix.result

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags,
  )

  container_port = 8000
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-${local.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.tags
}

# Identity of the application: pulls from ACR, reads Key Vault secrets,
# writes DLQ blobs and calls Azure OpenAI (see roles.tf).
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.name}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.tags
}

resource "azurerm_container_registry" "this" {
  name                = substr("acr${local.compact_name}${local.suffix}", 0, 50)
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = var.acr_sku
  admin_enabled       = false # pulls use the managed identity (AcrPull), never admin credentials
  tags                = local.tags
}
