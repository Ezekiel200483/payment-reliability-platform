# 🚀 SRE Financial Platform - Quick Setup Guide



## 🎯 What You're Building

A complete payment monitoring stack with:
- **Payment API** (FastAPI service)
- **Prometheus** (Metrics collection)
- **Grafana** (Beautiful dashboards)



---

## ⚡ Quick Start (5 Minutes)

### Step 1: Clone and Enter Directory
```bash
git clone <your-repo>
cd Project
```

### Step 2: Start the Monitoring Stack
```bash
# Option A: Full Docker Stack (Recommended)
docker-compose up -d

# Option B: Local Development
./start-dev.sh
```

### Step 3: Access Your Services
```bash
🔗 Payment API:    http://localhost:9000
📊 Prometheus:     http://localhost:9090  
🎨 Grafana:        http://localhost:3000
```

### Step 4: Create Test Payments
```bash
# Nigerian USSD payment
curl -X POST http://localhost:9000/payments \
  -H "Content-Type: application/json" \
  -d '{"amount": 2500, "currency": "NGN", "method": "ussd", "customer_id": "lagos_customer", "merchant_id": "gtbank"}'

# Large bank transfer
curl -X POST http://localhost:9000/payments \
  -H "Content-Type: application/json" \
  -d '{"amount": 150000, "currency": "NGN", "method": "bank_transfer", "customer_id": "enterprise_customer", "merchant_id": "interswitch"}'
```

**That's it! You now have a working SRE monitoring demo.** ✅

---

## 🐳 Dockerization Details (SRE Deep Dive)

### Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Payment API   │    │   Prometheus    │    │    Grafana      │
│   (Port 9000)   │───▶│   (Port 9090)   │───▶│   (Port 3000)   │
│   + /metrics    │    │   Scrapes API   │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### What's Inside docker-compose.yml

**Payment Service:**
- 🐍 Python FastAPI app in container
- 📊 Exposes `/metrics` endpoint for Prometheus
- 🔧 Auto-restarts if it crashes
- 💾 Logs everything to console

**Prometheus:**
- 📈 Scrapes payment service every 15 seconds
- 💿 Stores metrics data locally
- 🎯 Configured to find your API automatically

**Grafana:**
- 🎨 Pretty dashboards for your metrics
- 🔐 Default login: admin/admin
- 📊 Pre-configured to read from Prometheus

### Step-by-Step Container Setup

#### 1. Build the Payment Service Image
```bash
# Navigate to the service
cd services/payment-service

# Build the Docker image
docker build -t payment-service:latest .

# Verify the image was created
docker images | grep payment-service
```

#### 2. Start Everything with Docker Compose
```bash
# Go back to project root
cd ../../

# Start all services in background
docker-compose up -d

# Check everything is running
docker-compose ps
```

You should see:
```
       Name              Command               State            Ports
------------------------------------------------------------------------
grafana         /run.sh                      Up      0.0.0.0:3000->3000/tcp
payment-service python main.py              Up      0.0.0.0:9000->9000/tcp
prometheus      /bin/prometheus --config...  Up      0.0.0.0:9090->9090/tcp
```

#### 3. Verify Monitoring Pipeline

**Check Prometheus is scraping:**
```bash
# Open Prometheus
open http://localhost:9090





# Go to Status → Targets
# You should see "payment-service" as UP ✅
```

**Check Grafana can see data:**
```bash
# Open Grafana
open http://localhost:3000

# Login: admin / admin
# Go to Explore → Select Prometheus
# Type: payment_requests_total
# Click Run Query → You should see a graph! 📈
```


---

## 🔍 Troubleshooting (When Things Go Wrong)

### Problem: "Port already in use"
```bash
# Find what's using the port
lsof -i :9090

# Kill the process or use different ports
```

### Problem: "Target is down in Prometheus"
```bash
# Check if payment service is healthy
curl http://localhost:9000/health

# Check the logs
docker-compose logs payment-service
```

### Problem: "Grafana can't connect to Prometheus"
```bash
# Check Grafana config
docker-compose logs grafana

# Restart just Grafana
docker-compose restart grafana
```

---

## 🎤 Interview Demo Script (15 Minutes)

### Slide 1: "The Problem" (2 min)
"At Interswitch, payment reliability is critical. One minute of downtime = millions in lost revenue. 
This is how I'd set up monitoring for Nigerian payment systems."

### Slide 2: "The Solution" (3 min)
```bash
# Start the platform
docker-compose up -d

# Show everything is healthy
curl http://localhost:9000/health
```

### Slide 3: "Simulate Nigerian Payments" (5 min)
```bash
# USSD payment (common in Nigeria)
curl -X POST http://localhost:9000/payments \
  -d '{"amount": 2500, "currency": "NGN", "method": "ussd"}'

# High-value bank transfer
curl -X POST http://localhost:9000/payments \
  -d '{"amount": 150000, "currency": "NGN", "method": "bank_transfer"}'

# Failed transaction (testing error handling)
curl -X POST http://localhost:9000/payments \
  -d '{"amount": -100, "currency": "NGN", "method": "card"}'
```

### Slide 4: "Show Prometheus Metrics" (3 min)
- Open http://localhost:9090
- Show `payment_requests_total` increasing
- Show `payment_amount_naira_total` for business metrics
- Show `payment_errors_total` for reliability

### Slide 5: "Grafana Business Dashboard" (2 min)
- Open http://localhost:3000
- Show payment volume, success rates, error rates
- Emphasize "business metrics, not just tech metrics"

**Key Talking Points:**
- ✅ Business-aware monitoring (not just CPU/memory)
- ✅ Nigerian payment methods (USSD, bank transfers)
- ✅ Real-time fraud detection
- ✅ Financial compliance logging
- ✅ Quick incident response

---

## 🇳🇬 Nigerian Payment Context

This demo includes Nigerian-specific features:

**Payment Methods:**
- 📱 USSD (*737# codes)
- 💳 Bank transfers (very popular)
- 🏦 Card payments
- 📲 Mobile money

**Fraud Detection:**
- 🚨 High-value transaction alerts (>₦100,000)
- 🔍 Velocity checks (too many transactions)
- 📍 Geographic anomalies

**Business Metrics:**
- 💰 Transaction volume in Naira
- ⚡ Payment method popularity
- 🏃‍♂️ Processing speed per method
- 🎯 Success rates by bank

---

## 📚 Next Steps

1. **Add More Dashboards:** Create boards for each payment method
2. **Set Up Alerts:** PagerDuty integration for critical failures  
3. **Load Testing:** Use the `testing/load/` scripts
4. **Security:** Add authentication and audit logging
5. **Scaling:** Kubernetes deployment configs

**Remember:** As an SRE, your job is making payments reliable, fast, and observable! 🚀
