# Dead-letter queue for hallucination incidents (DLQ_BACKEND=azure_blob).
# The app writes one immutable JSON blob per incident under incidents/YYYY/MM/DD/<id>.json.

resource "azurerm_storage_account" "dlq" {
  name                     = substr("st${local.compact_name}${local.suffix}", 0, 24)
  location                 = azurerm_resource_group.this.location
  resource_group_name      = azurerm_resource_group.this.name
  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "ZRS"
  access_tier              = "Hot"

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  # The app authenticates with AZURE_STORAGE_CONNECTION_STRING (injected from Key Vault),
  # which requires shared keys. Set to false once the app moves to DefaultAzureCredential.
  shared_access_key_enabled = true

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "dlq" {
  name                  = var.dlq_container_name
  storage_account_id    = azurerm_storage_account.dlq.id
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "dlq" {
  storage_account_id = azurerm_storage_account.dlq.id

  rule {
    name    = "archive-incidents"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["${var.dlq_container_name}/incidents/"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = var.dlq_cool_tier_after_days
        tier_to_archive_after_days_since_modification_greater_than = var.dlq_archive_tier_after_days
      }

      version {
        change_tier_to_archive_after_days_since_creation = var.dlq_archive_tier_after_days
      }
    }
  }
}
