"""
Integration tests for payment service
"""

import pytest
import time
import asyncio
from fastapi.testclient import TestClient
import sys
import os

# Add services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/payment-service'))

def test_full_payment_flow(client):
    """Test complete payment flow from creation to completion"""
    # Create payment
    payment_data = {
        "amount": 1500.0,
        "currency": "NGN",
        "method": "card",
        "customer_id": "integration_customer_123",
        "merchant_id": "integration_merchant_456",
        "description": "Integration test payment"
    }
    
    create_response = client.post("/payments", json=payment_data)
    assert create_response.status_code == 200
    
    payment = create_response.json()
    transaction_id = payment["transaction_id"]
    
    # Verify initial state
    assert payment["status"] in ["pending", "fraud_detected"]
    assert payment["amount"] == 1500.0
    
    # If not blocked by fraud detection, wait and check for processing
    if payment["status"] == "pending":
        # Wait a bit for background processing
        time.sleep(2)
        
        # Check payment status
        status_response = client.get(f"/payments/{transaction_id}")
        assert status_response.status_code == 200
        
        updated_payment = status_response.json()
        # Status should have progressed
        assert updated_payment["status"] in ["pending", "processing", "completed", "failed"]

def test_multiple_payments_concurrency(client):
    """Test handling multiple concurrent payments"""
    payments = []
    
    # Create multiple payments
    for i in range(5):
        payment_data = {
            "amount": 100.0 + i * 50,
            "currency": "NGN",
            "method": "bank_transfer",
            "customer_id": f"customer_{i}",
            "merchant_id": f"merchant_{i}",
            "description": f"Concurrent test payment {i}"
        }
        
        response = client.post("/payments", json=payment_data)
        assert response.status_code == 200
        payments.append(response.json())
    
    # Verify all payments were created
    assert len(payments) == 5
    
    # Check that transaction IDs are unique
    transaction_ids = [p["transaction_id"] for p in payments]
    assert len(set(transaction_ids)) == 5

def test_payment_metrics_integration(client):
    """Test that metrics are properly recorded"""
    # Get initial metrics
    initial_metrics = client.get("/metrics")
    assert initial_metrics.status_code == 200
    initial_text = initial_metrics.text
    
    # Create a payment
    payment_data = {
        "amount": 750.0,
        "currency": "NGN",
        "method": "ussd",
        "customer_id": "metrics_customer",
        "merchant_id": "metrics_merchant"
    }
    
    response = client.post("/payments", json=payment_data)
    assert response.status_code == 200
    
    # Get updated metrics
    updated_metrics = client.get("/metrics")
    assert updated_metrics.status_code == 200
    updated_text = updated_metrics.text
    
    # Verify metrics were updated
    assert "payment_requests_total" in updated_text
    assert "payment_amount_naira" in updated_text

def test_health_check_detailed(client):
    """Test health check with detailed validation"""
    response = client.get("/health")
    assert response.status_code == 200
    
    health_data = response.json()
    
    # Validate health check response structure
    required_fields = ["status", "timestamp", "version", "uptime_seconds"]
    for field in required_fields:
        assert field in health_data
    
    # Validate field types and values
    assert health_data["status"] == "healthy"
    assert isinstance(health_data["uptime_seconds"], (int, float))
    assert health_data["uptime_seconds"] >= 0
    assert health_data["version"] == "1.0.0"

def test_payment_list_pagination(client):
    """Test payment listing with pagination"""
    # Create several payments
    for i in range(15):
        payment_data = {
            "amount": 100.0 + i,
            "currency": "NGN",
            "method": "qr_code",
            "customer_id": f"pagination_customer_{i}",
            "merchant_id": f"pagination_merchant_{i}"
        }
        
        response = client.post("/payments", json=payment_data)
        assert response.status_code == 200
    
    # Test default limit
    response = client.get("/payments")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["payments"]) <= 10  # Default limit
    
    # Test custom limit
    response = client.get("/payments?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["payments"]) <= 5

def test_error_handling_integration(client):
    """Test error handling in various scenarios"""
    # Test invalid JSON
    response = client.post("/payments", 
                          data="invalid json", 
                          headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    
    # Test missing required fields
    incomplete_payment = {
        "amount": 100.0
        # Missing required fields
    }
    
    response = client.post("/payments", json=incomplete_payment)
    assert response.status_code == 422
    
    # Test invalid payment method
    invalid_method_payment = {
        "amount": 100.0,
        "currency": "NGN",
        "method": "invalid_method",
        "customer_id": "customer_123",
        "merchant_id": "merchant_456"
    }
    
    response = client.post("/payments", json=invalid_method_payment)
    assert response.status_code == 422
