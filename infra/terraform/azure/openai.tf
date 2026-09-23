resource "azurerm_cognitive_account" "openai" {
  name                  = "oai-${local.name}-${local.suffix}"
  location              = azurerm_resource_group.this.location
  resource_group_name   = azurerm_resource_group.this.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.name}-${local.suffix}" # required for Entra ID (token) auth

  # The app currently authenticates with AZURE_OPENAI_API_KEY (injected from Key Vault).
  # Set to false once it uses the managed identity (Cognitive Services OpenAI User is already granted).
  local_auth_enabled            = true
  public_network_access_enabled = true

  identity {
    type = "SystemAssigned"
  }

  tags = local.tags
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.openai_chat_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.openai_chat_model.name
    version = var.openai_chat_model.version
  }

  sku {
    name     = var.openai_deployment_sku
    capacity = var.openai_chat_capacity
  }
}

resource "azurerm_cognitive_deployment" "embeddings" {
  name                 = var.openai_embed_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = var.openai_embed_model.name
    version = var.openai_embed_model.version
  }

  sku {
    name     = var.openai_deployment_sku
    capacity = var.openai_embed_capacity
  }

  # Deployments on the same account are updated sequentially by the service.
  depends_on = [azurerm_cognitive_deployment.chat]
}
