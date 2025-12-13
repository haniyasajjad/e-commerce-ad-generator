#!/bin/bash
# Test deployment on local Kind cluster (FREE)

set -e

echo "🎯 Testing on Kind cluster (Local Kubernetes)"

# Check if Kind cluster exists
if ! kubectl cluster-info --context kind-kind &> /dev/null; then
    echo "❌ Kind cluster not found. Creating..."
    cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 8080
    protocol: TCP
  - containerPort: 30001
    hostPort: 8001
    protocol: TCP
EOF
else
    echo "✅ Kind cluster already exists"
fi

# Switch to Kind context
kubectl config use-context kind-kind

# Create namespace
echo "📦 Creating namespace..."
kubectl create namespace ad-creative --dry-run=client -o yaml | kubectl apply -f -

# Build and load image into Kind
echo "🐳 Building Docker image..."
docker build -t ad-creative-api:local .

echo "📥 Loading image into Kind..."
kind load docker-image ad-creative-api:local

# Create ConfigMap
echo "⚙️  Creating ConfigMap..."
kubectl create configmap ad-creative-config \
  --from-literal=MLFLOW_TRACKING_URI=http://mlflow:5000 \
  --from-literal=LOG_LEVEL=INFO \
  --namespace=ad-creative \
  --dry-run=client -o yaml | kubectl apply -f -

# Create a Kind-specific deployment (no LoadBalancer)
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ad-creative-api
  namespace: ad-creative
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ad-creative-api
  template:
    metadata:
      labels:
        app: ad-creative-api
    spec:
      containers:
      - name: ad-creative
        image: ad-creative-api:local
        imagePullPolicy: Never
        ports:
        - containerPort: 8000
        env:
        - name: MLFLOW_TRACKING_URI
          valueFrom:
            configMapKeyRef:
              name: ad-creative-config
              key: MLFLOW_TRACKING_URI
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: ad-creative-service
  namespace: ad-creative
spec:
  type: NodePort
  selector:
    app: ad-creative-api
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
    nodePort: 30080
    name: http
  - protocol: TCP
    port: 8001
    targetPort: 8001
    nodePort: 30001
    name: metrics
EOF

# Wait for deployment
echo "⏳ Waiting for deployment..."
kubectl rollout status deployment/ad-creative-api -n ad-creative --timeout=3m

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Status:"
kubectl get all -n ad-creative

echo ""
echo "🌐 Access your API:"
echo "  Health: http://localhost:8080/health"
echo "  Docs: http://localhost:8080/docs"
echo "  Metrics: http://localhost:8001/metrics"
echo ""
echo "🧪 Test command:"
echo "  curl http://localhost:8080/health"
echo ""
echo "📝 View logs:"
echo "  kubectl logs -l app=ad-creative-api -n ad-creative --follow"