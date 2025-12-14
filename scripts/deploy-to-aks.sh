#!/bin/bash
# Quick deploy to AKS

set -e

NAMESPACE="ad-creative"

echo "🚀 Deploying to AKS..."

# 1. Update image in deployment.yaml
read -p "Enter your Docker Hub username: " DOCKER_USER
sed -i.bak "s|<your-dockerhub-username>|$DOCKER_USER|g" k8s/deployment.yaml

# 2. Apply all manifests
echo "📦 Applying Kubernetes manifests..."
kubectl apply -f k8s/deployment.yaml -n $NAMESPACE

# 3. Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/ad-creative-api -n $NAMESPACE --timeout=5m

# 4. Get service info
echo "📊 Service Status:"
kubectl get all -n $NAMESPACE

# 5. Get external IP
echo ""
echo "🌐 Getting external IP (this may take 2-3 minutes)..."
echo "Run this command to check:"
echo "  kubectl get service ad-creative-service -n $NAMESPACE --watch"
echo ""

# Wait for external IP
EXTERNAL_IP=""
for i in {1..60}; do
  EXTERNAL_IP=$(kubectl get service ad-creative-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
  if [ -n "$EXTERNAL_IP" ]; then
    break
  fi
  echo "Waiting for external IP... (${i}/60)"
  sleep 5
done

if [ -n "$EXTERNAL_IP" ]; then
  echo ""
  echo "✅ Deployment successful!"
  echo ""
  echo "🎯 Your API is available at:"
  echo "  Health: http://$EXTERNAL_IP/health"
  echo "  Docs: http://$EXTERNAL_IP/docs"
  echo "  Generate: POST http://$EXTERNAL_IP/generate"
  echo "  Metrics: http://$EXTERNAL_IP:8001/metrics"
  echo ""
  echo "🧪 Test it:"
  echo "  curl http://$EXTERNAL_IP/health"
else
  echo "⚠️  External IP not yet assigned. Check with:"
  echo "  kubectl get service ad-creative-service -n $NAMESPACE"
fi

# 6. Show logs
echo ""
echo "📝 Recent logs:"
kubectl logs -l app=ad-creative-api -n $NAMESPACE --tail=20

echo ""
echo "✅ Deployment complete!"