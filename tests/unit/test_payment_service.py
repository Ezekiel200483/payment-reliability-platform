"""
Unit tests for payment service
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Add services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/payment-service'))

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "uptime_seconds" in data

def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

def test_create_payment_valid(client):
    """Test creating a valid payment"""
    payment_data = {
        "amount": 1000.0,
        "currency": "NGN",
        "method": "card",
        "customer_id": "customer_123",
        "merchant_id": "merchant_456",
        "description": "Test payment"
    }
    
    response = client.post("/payments", json=payment_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "transaction_id" in data
    assert data["status"] in ["pending", "fraud_detected"]
    assert data["amount"] == 1000.0
    assert data["currency"] == "NGN"
    assert data["method"] == "card"
    assert "risk_score" in data

def test_create_payment_invalid_amount(client):
    """Test creating payment with invalid amount"""
    payment_data = {
        "amount": -100.0,  # Invalid negative amount
        "currency": "NGN",
        "method": "card",
        "customer_id": "customer_123",
        "merchant_id": "merchant_456"
    }
    
    response = client.post("/payments", json=payment_data)
    assert response.status_code == 422  # Validation error

def test_get_payment_not_found(client):
    """Test getting a non-existent payment"""
    response = client.get("/payments/non-existent-id")
    assert response.status_code == 404

def test_get_payment_found(client):
    """Test getting an existing payment"""
    # First create a payment
    payment_data = {
        "amount": 500.0,
        "currency": "NGN",
        "method": "bank_transfer",
        "customer_id": "customer_789",
        "merchant_id": "merchant_123"
    }
    
    create_response = client.post("/payments", json=payment_data)
    assert create_response.status_code == 200
    
    transaction_id = create_response.json()["transaction_id"]
    
    # Then get the payment
    get_response = client.get(f"/payments/{transaction_id}")
    assert get_response.status_code == 200
    
    data = get_response.json()
    assert data["transaction_id"] == transaction_id
    assert data["amount"] == 500.0

def test_list_payments(client):
    """Test listing payments"""
    response = client.get("/payments")
    assert response.status_code == 200
    
    data = response.json()
    assert "payments" in data
    assert "total" in data
    assert isinstance(data["payments"], list)

def test_list_payments_with_status_filter(client):
    """Test listing payments with status filter"""
    response = client.get("/payments?status=pending")
    assert response.status_code == 200
    
    data = response.json()
    assert "payments" in data
    assert "total" in data

@pytest.mark.asyncio
async def test_fraud_check():
    """Test fraud detection logic"""
    from main import check_fraud_risk, PaymentRequest, PaymentMethod
    
    # Low risk payment
    low_risk_payment = PaymentRequest(
        amount=100.0,
        method=PaymentMethod.BANK_TRANSFER,
        customer_id="customer_123",
        merchant_id="merchant_456"
    )
    
    risk_score = await check_fraud_risk(low_risk_payment)
    assert 0.0 <= risk_score <= 1.0
    
    # High risk payment
    high_risk_payment = PaymentRequest(
        amount=200000.0,  # Very high amount
        method=PaymentMethod.CARD,
        customer_id="customer_123",
        merchant_id="merchant_456"
    )
    
    risk_score = await check_fraud_risk(high_risk_payment)
    assert 0.0 <= risk_score <= 1.0
