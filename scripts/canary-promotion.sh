#!/bin/bash
# Canary Deployment Promotion Script
# Gradually promotes canary to stable if metrics are good

set -e

echo "🚀 Starting Canary Deployment Promotion"

# Configuration
NAMESPACE="default"
STABLE_DEPLOYMENT="ad-creative-stable"
CANARY_DEPLOYMENT="ad-creative-canary"
PROMETHEUS_URL="http://localhost:9090"
OBSERVATION_WINDOW="5m"

# Canary stages (percentage of traffic)
STAGES=(10 25 50 75 100)

# Metric thresholds for promotion
MAX_ERROR_RATE=0.05      # 5%
MAX_P95_LATENCY=5.0      # 5 seconds
MIN_QUALITY_SCORE=0.5    # 0-1 scale

check_metrics() {
    local version=$1
    echo "📊 Checking metrics for version: $version"
    
    # Query Prometheus for error rate
    ERROR_RATE=$(curl -s "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=rate(ad_requests_total{version=\"${version}\",status=\"error\"}[${OBSERVATION_WINDOW}]) / rate(ad_requests_total{version=\"${version}\"}[${OBSERVATION_WINDOW}])" \
        | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    # Query for P95 latency
    P95_LATENCY=$(curl -s "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=histogram_quantile(0.95, rate(ad_latency_seconds_bucket{version=\"${version}\"}[${OBSERVATION_WINDOW}]))" \
        | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    # Query for median quality score
    QUALITY_SCORE=$(curl -s "${PROMETHEUS_URL}/api/v1/query" \
        --data-urlencode "query=histogram_quantile(0.50, rate(ad_quality_score_bucket{version=\"${version}\"}[${OBSERVATION_WINDOW}]))" \
        | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "0")
    
    echo "   Error Rate: ${ERROR_RATE}"
    echo "   P95 Latency: ${P95_LATENCY}s"
    echo "   Quality Score: ${QUALITY_SCORE}"
    
    # Check thresholds
    if (( $(echo "$ERROR_RATE > $MAX_ERROR_RATE" | bc -l) )); then
        echo "❌ Error rate too high (${ERROR_RATE} > ${MAX_ERROR_RATE})"
        return 1
    fi
    
    if (( $(echo "$P95_LATENCY > $MAX_P95_LATENCY" | bc -l) )); then
        echo "❌ Latency too high (${P95_LATENCY} > ${MAX_P95_LATENCY})"
        return 1
    fi
    
    if (( $(echo "$QUALITY_SCORE < $MIN_QUALITY_SCORE" | bc -l) )); then
        echo "❌ Quality score too low (${QUALITY_SCORE} < ${MIN_QUALITY_SCORE})"
        return 1
    fi
    
    echo "✅ All metrics within acceptable range"
    return 0
}

rollback_canary() {
    echo "🔄 Rolling back canary deployment..."
    kubectl scale deployment/${CANARY_DEPLOYMENT} --replicas=0 -n ${NAMESPACE}
    echo "❌ Canary rollback complete"
    exit 1
}

promote_stage() {
    local stage=$1
    local total_replicas=10
    local canary_replicas=$((total_replicas * stage / 100))
    local stable_replicas=$((total_replicas - canary_replicas))
    
    echo "📈 Promoting to stage: ${stage}%"
    echo "   Stable replicas: ${stable_replicas}"
    echo "   Canary replicas: ${canary_replicas}"
    
    # Scale deployments
    kubectl scale deployment/${STABLE_DEPLOYMENT} --replicas=${stable_replicas} -n ${NAMESPACE}
    kubectl scale deployment/${CANARY_DEPLOYMENT} --replicas=${canary_replicas} -n ${NAMESPACE}
    
    # Wait for rollout
    kubectl rollout status deployment/${CANARY_DEPLOYMENT} -n ${NAMESPACE} --timeout=5m
    
    echo "⏳ Waiting 2 minutes for metrics to stabilize..."
    sleep 120
    
    # Check metrics
    if ! check_metrics "canary"; then
        echo "⚠️ Metrics check failed at ${stage}% stage"
        rollback_canary
    fi
    
    echo "✅ Stage ${stage}% passed"
}

# Main promotion flow
echo "Starting canary promotion with stages: ${STAGES[*]}"

for stage in "${STAGES[@]}"; do
    promote_stage $stage
done

# Full promotion - replace stable with canary
echo "🎉 Canary fully validated! Promoting to stable..."

# Get canary image
CANARY_IMAGE=$(kubectl get deployment/${CANARY_DEPLOYMENT} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}')

# Update stable deployment with canary image
kubectl set image deployment/${STABLE_DEPLOYMENT} ad-creative=${CANARY_IMAGE} -n ${NAMESPACE}
kubectl rollout status deployment/${STABLE_DEPLOYMENT} -n ${NAMESPACE} --timeout=5m

# Scale stable back to full capacity
kubectl scale deployment/${STABLE_DEPLOYMENT} --replicas=10 -n ${NAMESPACE}

# Remove canary deployment
kubectl scale deployment/${CANARY_DEPLOYMENT} --replicas=0 -n ${NAMESPACE}

echo "✅ Canary promotion complete!"
echo "   New stable image: ${CANARY_IMAGE}"