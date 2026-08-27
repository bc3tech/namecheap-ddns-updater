#!/usr/bin/env sh
set -eu

resource_id="$(azd env get-value AZURE_RESOURCE_NAMECHEAP_DDNS_UPDATER_ID)"
if [ -z "$resource_id" ]; then
    echo "AZURE_RESOURCE_NAMECHEAP_DDNS_UPDATER_ID is not set" >&2
    exit 1
fi

az containerapp update \
    --ids "$resource_id" \
    --min-replicas 0 \
    --max-replicas 1 \
    --output none
