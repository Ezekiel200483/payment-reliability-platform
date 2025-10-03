#!/bin/bash

# SRE Financial Platform - Quick Start Script
# This script demonstrates the platform capabilities

set -e

echo "🚀 Starting SRE Financial Services Platform..."
echo "======================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

echo "✅ Docker is running"

# Start the payment service in development mode
echo "🔧 Starting Payment Service (Development Mode)..."
cd services/payment-service

# Activate virtual environment if it exists
if [ -d "../../venv" ]; then
    source ../../venv/bin/activate
    echo "✅ Activated Python virtual environment"
fi

# Install dependencies if needed
if [ ! -f "../../venv/lib/python3.9/site-packages/fastapi/__init__.py" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
fi

echo "🌟 Starting Payment Service on http://localhost:8000"
echo "📊 Metrics available on http://localhost:8001/metrics"
echo "📚 API docs available on http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Start the service
python main.py
