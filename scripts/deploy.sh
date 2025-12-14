#!/bin/bash
# Manual CI/CD Pipeline Simulation
# Replicates GitHub Actions workflow locally
# Updated to read Docker credentials from .env.docker

set -e

# ============================================
# Load environment variables
# ============================================
if [ -f ".env.docker" ]; then
    echo "→ Loading Docker credentials from .env.docker"
    export $(grep -v '^#' .env.docker | xargs)
else
    echo "⚠ .env.docker file not found!"
    echo "Please create a .env.docker file with DOCKER_USER and DOCKER_TOKEN"
    exit 1
fi

# ============================================
# JOB 3: DEPLOY
# ============================================
echo -e "${BLUE}=========================================="
echo "JOB 3: Deploy to Azure Kubernetes"
echo -e "==========================================${NC}"
echo ""

echo "→ Checking Azure login status..."
if ! az account show &>/dev/null; then
    echo "  Logging into Azure..."
    az login
fi

echo "→ Checking if AKS cluster exists..."
if ! az aks show --resource-group ad-creative-rg --name ad-creative-aks &>/dev/null; then
    echo "  Creating AKS cluster (this takes ~10 minutes)..."
    ./scripts/setup-aks-free.sh
else
    echo "  ✓ AKS cluster already exists"
fi

echo "→ Getting AKS credentials..."
az aks get-credentials \
    --resource-group ad-creative-rg \
    --name ad-creative-aks \
    --overwrite-existing

echo "→ Creating namespace..."
kubectl create namespace ad-creative --dry-run=client -o yaml | kubectl apply -f -

echo "→ Creating Docker Hub secret..."
kubectl create secret docker-registry dockerhub-secret \
    --docker-server=https://index.docker.io/v1/ \
    --docker-username=${DOCKER_USER} \
    --docker-password=${DOCKER_TOKEN} \
    --namespace=ad-creative \
    --dry-run=client -o yaml | kubectl apply -f -

echo "→ Creating ConfigMap..."
kubectl create configmap ad-creative-config \
    --from-literal=MLFLOW_TRACKING_URI=http://mlflow:5000 \
    --from-literal=LOG_LEVEL=INFO \
    --namespace=ad-creative \
    --dry-run=client -o yaml | kubectl apply -f -

echo "→ Updating deployment manifest with image..."
sed -i.bak "s|<your-dockerhub-username>|${DOCKER_USER}|g" k8s/deployment.yaml

echo "→ Applying Kubernetes manifests..."
kubectl apply -f k8s/deployment.yaml -n ad-creative

echo "→ Waiting for rollout to complete..."
kubectl rollout status deployment/ad-creative-api -n ad-creative 

echo -e "${GREEN}✅ DEPLOY JOB PASSED${NC}"
sleep 2

# ============================================
# VERIFICATION
# ============================================
echo -e "${BLUE}=========================================="
echo "DEPLOYMENT VERIFICATION"
echo -e "==========================================${NC}"
echo ""

kubectl get deployment ad-creative-api -n ad-creative
kubectl get pods -n ad-creative
kubectl get service ad-creative-service -n ad-creative
kubectl get hpa ad-creative-hpa -n ad-creative
kubectl get configmap ad-creative-config -n ad-creative

echo ""
echo "→ Getting external IP (may take 2-3 minutes)..."
EXTERNAL_IP=""
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get service ad-creative-service -n ad-creative -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$EXTERNAL_IP" ]; then
        break
    fi
    echo "  Waiting... (${i}/30)"
    sleep 5
done

if [ -n "$EXTERNAL_IP" ]; then
    echo -e "${GREEN}🎯 Your application is live at: http://${EXTERNAL_IP}${NC}"
else
    echo "⚠️  External IP not yet assigned. Check with:"
    echo "   kubectl get service ad-creative-service -n ad-creative --watch"
fi

echo ""
echo "📊 Full status:"
kubectl get all -n ad-creative

echo ""
echo "💾 To save costs, remember to cleanup:"
echo "   ./scripts/cleanup-azure.sh"
echo ""
