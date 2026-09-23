# PostgreSQL Flexible Server 16 for the pgvector Gold layer (VECTOR_STORE=pgvector).
#
# Azure requires extensions to be allow-listed (azure.extensions = VECTOR below);
# the extension is then enabled once per database by the admin (SQL step):
#
#   CREATE EXTENSION IF NOT EXISTS vector;
#   CREATE ROLE rag_app LOGIN PASSWORD '<password>';
#   GRANT CONNECT ON DATABASE rag TO rag_app;
#   GRANT USAGE, CREATE ON SCHEMA public TO rag_app;
#
# The resulting DSN for rag_app is stored in the Key Vault secret "pgvector-dsn".

resource "random_password" "postgres_admin" {
  length           = 32
  special          = true
  override_special = "-_.~"
}

resource "azurerm_postgresql_flexible_server" "this" {
  name                = "psql-${local.name}-${local.suffix}"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  version             = "16"
  sku_name            = var.postgres_sku_name
  storage_mb          = var.postgres_storage_mb
  auto_grow_enabled   = true

  administrator_login    = var.postgres_admin_login
  administrator_password = random_password.postgres_admin.result

  # Private access only: VNet-integrated, no public endpoint.
  delegated_subnet_id           = azurerm_subnet.postgres.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false

  backup_retention_days        = var.postgres_backup_retention_days
  geo_redundant_backup_enabled = false

  dynamic "high_availability" {
    for_each = var.postgres_high_availability ? [1] : []

    content {
      mode = "ZoneRedundant"
    }
  }

  tags = local.tags

  # Zone placement is chosen by Azure; ignore it to avoid spurious diffs after failover.
  lifecycle {
    ignore_changes = [zone, high_availability[0].standby_availability_zone]
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "VECTOR"
}

resource "azurerm_postgresql_flexible_server_configuration" "require_tls" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "on"
}

resource "azurerm_postgresql_flexible_server_database" "rag" {
  name      = var.postgres_database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
