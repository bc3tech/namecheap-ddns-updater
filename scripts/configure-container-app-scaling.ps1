$ErrorActionPreference = 'Stop'

$resourceId = azd env get-value AZURE_RESOURCE_NAMECHEAP_DDNS_UPDATER_ID
if ([string]::IsNullOrWhiteSpace($resourceId)) {
    throw 'AZURE_RESOURCE_NAMECHEAP_DDNS_UPDATER_ID is not set'
}

az containerapp update `
    --ids $resourceId `
    --min-replicas 0 `
    --max-replicas 1 `
    --output none

if ($LASTEXITCODE -ne 0) {
    throw "Failed to configure Container App scaling for $resourceId"
}
