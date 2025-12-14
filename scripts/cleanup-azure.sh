#!/bin/bash
# Cleanup Azure resources to STOP costs

set -e

RESOURCE_GROUP="ad-creative-rg"
AKS_NAME="ad-creative-aks"

echo "🧹 Azure Cleanup Script"
echo "======================="
echo ""
echo "This will DELETE:"
echo "  - AKS cluster: $AKS_NAME"
echo "  - Resource group: $RESOURCE_GROUP"
echo "  - All associated resources (VMs, Load Balancers, Disks, etc.)"
echo ""
read -p "Are you sure? This cannot be undone. (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ Cleanup cancelled"
  exit 0
fi

echo ""
echo "Option 1: STOP cluster (can restart later, minimal cost)"
echo "Option 2: DELETE everything (no cost, cannot recover)"
echo ""
read -p "Choose (1=stop, 2=delete): " OPTION

if [ "$OPTION" = "1" ]; then
  echo "⏸️  Stopping AKS cluster..."
  az aks stop --resource-group $RESOURCE_GROUP --name $AKS_NAME
  echo "✅ Cluster stopped. To restart:"
  echo "   az aks start --resource-group $RESOURCE_GROUP --name $AKS_NAME"
  
elif [ "$OPTION" = "2" ]; then
  echo "🗑️  Deleting resource group (this takes 5-10 minutes)..."
  az group delete \
    --name $RESOURCE_GROUP \
    --yes \
    --no-wait
  
  echo "✅ Deletion initiated. Check status:"
  echo "   az group show --name $RESOURCE_GROUP"
  echo ""
  echo "Once deleted, all costs will stop immediately."
  
else
  echo "❌ Invalid option"
  exit 1
fi

echo ""
echo "💰 Cost Summary:"
echo "  - Before cleanup: ~$1.20/day"
echo "  - After stop: ~$0.10/day (just storage)"
echo "  - After delete: $0.00/day"