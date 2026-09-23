terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state is intentionally not configured: this module is validated only,
  # never applied. For a real deployment, use an Azure Storage backend with Entra ID auth:
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-tfstate"
  #   storage_account_name = "sttfstate<unique>"
  #   container_name       = "tfstate"
  #   key                  = "legal-rag/azure/terraform.tfstate"
  #   use_azuread_auth     = true
  # }
}

provider "azurerm" {
  # azurerm 4.x requires an explicit subscription (or ARM_SUBSCRIPTION_ID at runtime).
  subscription_id = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }

    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}
