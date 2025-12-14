#!/bin/bash
# FREE AKS Setup for Azure Students
# Uses minimal resources to stay within free tier

set -e

# Configuration
RESOURCE_GROUP="ad-creative-rg"
LOCATION="eastus"  # Change to your nearest region
AKS_NAME="ad-creative-aks"
NODE_COUNT=1  # Start with 1 node (FREE tier)
NODE_SIZE="Standard_B2s"  # Cheapest VM size (2 vCPU, 4GB RAM)

echo "🚀 Setting up FREE AKS cluster for MLOps project..."

# 1. Login to Azure
echo "📋 Step 1: Login to Azure"
az login

# 2. Create Resource Group
echo "📋 Step 2: Creating resource group: $RESOURCE_GROUP"
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 3. Create AKS Cluster (FREE TIER)
echo "📋 Step 3: Creating AKS cluster (this takes 5-10 minutes)..."
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --node-count $NODE_COUNT \
  --node-vm-size $NODE_SIZE \
  --enable-managed-identity \
  --generate-ssh-keys \
  --tier free \
  --no-wait

echo "⏳ Waiting for AKS cluster to be ready..."
az aks wait --created --resource-group $RESOURCE_GROUP --name $AKS_NAME

# 4. Get credentials
echo "📋 Step 4: Getting AKS credentials"
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --overwrite-existing

# 5. Verify connection
echo "📋 Step 5: Verifying cluster connection"
kubectl cluster-info
kubectl get nodes

# 6. Create namespace
echo "📋 Step 6: Creating namespace"
kubectl create namespace ad-creative || echo "Namespace already exists"

# 7. Create Docker Hub secret
echo "📋 Step 7: Setting up Docker Hub credentials"
read -p "Enter Docker Hub username: " DOCKER_USER
read -sp "Enter Docker Hub token: " DOCKER_TOKEN
echo ""

kubectl create secret docker-registry dockerhub-secret \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username=$DOCKER_USER \
  --docker-password=$DOCKER_TOKEN \
  --namespace=ad-creative \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ AKS setup complete!"
echo ""
echo "📊 Cluster Info:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Cluster Name: $AKS_NAME"
echo "  Location: $LOCATION"
echo "  Nodes: $NODE_COUNT x $NODE_SIZE"
echo ""
echo "🎯 Next steps:"
echo "  1. Update k8s/deployment.yaml with your Docker Hub username"
echo "  2. Deploy: kubectl apply -f k8s/ -n ad-creative"
echo "  3. Check status: kubectl get all -n ad-creative"
echo ""
echo "⚠️  COST WARNING:"
echo "  - AKS control plane: FREE (free tier)"
echo "  - VM cost: ~$0.04/hour (~$30/month for 1 node)"
echo "  - LoadBalancer: ~$0.005/hour (~$3.60/month)"
echo "  - TOTAL: ~$35/month if left running"
echo ""
echo "💡 To STOP costs after demo:"
echo "  az aks stop --resource-group $RESOURCE_GROUP --name $AKS_NAME"
echo ""
echo "🗑️  To DELETE everything:"
echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"