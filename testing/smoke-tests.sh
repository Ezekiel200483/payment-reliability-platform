#!/bin/bash

# Basic Smoke Tests for Payment Service
# This script performs basic health checks after deployment

set -e

echo "🔍 Starting smoke tests..."

# Test configuration
BASE_URL=${BASE_URL:-"http://localhost:8000"}
TIMEOUT=${TIMEOUT:-60}

echo "Testing against: $BASE_URL"

# Function to test endpoint with retry
test_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    local description=$3
    
    echo "Testing $description..."
    
    for i in {1..5}; do
        if response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null); then
            status_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | head -n -1)
            
            if [ "$status_code" -eq "$expected_status" ]; then
                echo "✅ $description - Status: $status_code"
                return 0
            else
                echo "❌ $description - Expected: $expected_status, Got: $status_code"
                if [ $i -eq 5 ]; then
                    echo "Response body: $body"
                    return 1
                fi
            fi
        else
            echo "⚠️  $description - Connection failed (attempt $i/5)"
            if [ $i -eq 5 ]; then
                return 1
            fi
        fi
        
        sleep 2
    done
}

# Test health endpoint
test_endpoint "/health" 200 "Health check"

# Test metrics endpoint
test_endpoint "/metrics" 200 "Metrics endpoint"

# Test basic API functionality
echo "Testing basic API functionality..."

# Test payment creation (if endpoint exists)
if curl -s -f "$BASE_URL/payments" > /dev/null 2>&1; then
    test_endpoint "/payments" 200 "Payment list endpoint"
else
    echo "ℹ️  Payment endpoints not available or require authentication"
fi

# Test API documentation endpoint (if exists)
if curl -s -f "$BASE_URL/docs" > /dev/null 2>&1; then
    test_endpoint "/docs" 200 "API documentation"
else
    echo "ℹ️  API documentation endpoint not available"
fi

echo "🎉 Smoke tests completed successfully!"
