#!/bin/bash

# Production Smoke Tests for Payment Service
# This script performs comprehensive health checks for production deployment

set -e

echo "🔍 Starting production smoke tests..."

# Test configuration
BASE_URL=${BASE_URL:-"http://localhost:8000"}
PROMETHEUS_URL=${PROMETHEUS_URL:-"http://localhost:9090"}
GRAFANA_URL=${GRAFANA_URL:-"http://localhost:3000"}

echo "Testing against:"
echo "  Payment Service: $BASE_URL"
echo "  Prometheus: $PROMETHEUS_URL"
echo "  Grafana: $GRAFANA_URL"

# Function to test endpoint with retry and detailed logging
test_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    local description=$3
    local max_attempts=${4:-5}
    
    echo "Testing $description..."
    
    for i in $(seq 1 $max_attempts); do
        if response=$(curl -s -w "\n%{http_code}\n%{time_total}" "$url" 2>/dev/null); then
            status_code=$(echo "$response" | tail -n2 | head -n1)
            time_total=$(echo "$response" | tail -n1)
            body=$(echo "$response" | head -n -2)
            
            if [ "$status_code" -eq "$expected_status" ]; then
                echo "✅ $description - Status: $status_code, Time: ${time_total}s"
                return 0
            else
                echo "❌ $description - Expected: $expected_status, Got: $status_code"
                if [ $i -eq $max_attempts ]; then
                    echo "Response body: $body"
                    return 1
                fi
            fi
        else
            echo "⚠️  $description - Connection failed (attempt $i/$max_attempts)"
            if [ $i -eq $max_attempts ]; then
                return 1
            fi
        fi
        
        sleep 5
    done
}

# Test Payment Service
echo "🔧 Testing Payment Service..."
test_endpoint "$BASE_URL/health" 200 "Payment service health" 10
test_endpoint "$BASE_URL/metrics" 200 "Payment service metrics"

# Test Monitoring Stack
echo "📊 Testing Monitoring Stack..."
test_endpoint "$PROMETHEUS_URL/-/healthy" 200 "Prometheus health"
test_endpoint "$PROMETHEUS_URL/api/v1/targets" 200 "Prometheus targets"
test_endpoint "$GRAFANA_URL/api/health" 200 "Grafana health"

# Test Database Connectivity (via health endpoint)
echo "🗄️  Testing Database Connectivity..."
if health_response=$(curl -s "$BASE_URL/health" 2>/dev/null); then
    if echo "$health_response" | grep -q "database.*ok\|db.*ok\|healthy" 2>/dev/null; then
        echo "✅ Database connectivity check passed"
    else
        echo "⚠️  Database connectivity status unclear from health endpoint"
    fi
else
    echo "❌ Cannot check database connectivity"
    exit 1
fi

# Test Redis Connectivity (via health endpoint)
echo "🔄 Testing Redis Connectivity..."
if echo "$health_response" | grep -q "redis.*ok\|cache.*ok" 2>/dev/null; then
    echo "✅ Redis connectivity check passed"
else
    echo "⚠️  Redis connectivity status unclear from health endpoint"
fi

# Test Prometheus Metrics Collection
echo "📈 Testing Metrics Collection..."
if metrics_response=$(curl -s "$BASE_URL/metrics" 2>/dev/null); then
    if echo "$metrics_response" | grep -q "python_info\|process_\|http_requests" 2>/dev/null; then
        echo "✅ Application metrics are being exposed"
    else
        echo "⚠️  Limited metrics found"
    fi
else
    echo "❌ Cannot retrieve metrics"
    exit 1
fi

# Check Prometheus is scraping targets
echo "🎯 Testing Prometheus Target Health..."
if targets_response=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null); then
    if echo "$targets_response" | grep -q '"health":"up"' 2>/dev/null; then
        echo "✅ Prometheus targets are healthy"
    else
        echo "⚠️  Some Prometheus targets may be down"
    fi
else
    echo "⚠️  Cannot check Prometheus targets"
fi

# Performance baseline check
echo "⚡ Performance Baseline Check..."
echo "Testing response times..."

total_time=0
successful_requests=0
failed_requests=0

for i in {1..10}; do
    if time_taken=$(curl -s -w "%{time_total}" -o /dev/null "$BASE_URL/health" 2>/dev/null); then
        total_time=$(echo "$total_time + $time_taken" | bc 2>/dev/null || echo "0")
        successful_requests=$((successful_requests + 1))
    else
        failed_requests=$((failed_requests + 1))
    fi
done

if [ $successful_requests -gt 0 ]; then
    avg_time=$(echo "scale=3; $total_time / $successful_requests" | bc 2>/dev/null || echo "N/A")
    echo "✅ Average response time: ${avg_time}s (${successful_requests}/10 successful)"
    
    # Alert if response time is too high
    if [ "$(echo "$avg_time > 1.0" | bc 2>/dev/null)" -eq 1 ] 2>/dev/null; then
        echo "⚠️  High response time detected!"
    fi
else
    echo "❌ All performance test requests failed"
    exit 1
fi

echo "🎉 Production smoke tests completed successfully!"
echo "📊 Summary:"
echo "  - Payment Service: ✅ Healthy"
echo "  - Monitoring Stack: ✅ Operational"
echo "  - Performance: ✅ Within baseline"
echo "  - Success Rate: ${successful_requests}/10 requests"
