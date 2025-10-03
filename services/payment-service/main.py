from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import structlog
import asyncio
import random
import time
from datetime import datetime, timezone
from enum import Enum
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, start_http_server, generate_latest
from fastapi.responses import Response
import uuid

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
PAYMENT_REQUESTS = Counter('payment_requests_total', 'Total payment requests', ['method', 'status'])
PAYMENT_LATENCY = Histogram('payment_request_duration_seconds', 'Payment request latency')
PAYMENT_AMOUNT = Histogram('payment_amount_naira', 'Payment amounts in Naira', buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000, float('inf')])
ACTIVE_PAYMENTS = Gauge('active_payments', 'Number of active payments')
FRAUD_DETECTIONS = Counter('fraud_detections_total', 'Total fraud detections', ['risk_level'])

# FastAPI app
app = FastAPI(
    title="Payment Service",
    description="Core payment processing service for Interswitch-style financial platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FRAUD_DETECTED = "fraud_detected"

class PaymentMethod(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    USSD = "ussd"
    QR_CODE = "qr_code"

class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount in Naira")
    currency: str = Field(default="NGN", description="Currency code")
    method: PaymentMethod = Field(..., description="Payment method")
    customer_id: str = Field(..., description="Customer identifier")
    merchant_id: str = Field(..., description="Merchant identifier")
    description: Optional[str] = Field(None, description="Payment description")
    callback_url: Optional[str] = Field(None, description="Callback URL for notifications")

class PaymentResponse(BaseModel):
    transaction_id: str
    status: PaymentStatus
    amount: float
    currency: str
    method: PaymentMethod
    created_at: datetime
    estimated_completion: Optional[datetime] = None
    risk_score: float
    
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float

# In-memory storage (in production, use a database)
payments_db: Dict[str, PaymentResponse] = {}
start_time = time.time()

# Circuit breaker for external services
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise e

# Global circuit breaker instance
fraud_service_cb = CircuitBreaker()

async def check_fraud_risk(payment: PaymentRequest) -> float:
    """Mock fraud detection service with circuit breaker"""
    # Simulate network latency
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    # Simulate occasional service failures
    if random.random() < 0.05:  # 5% failure rate
        raise Exception("Fraud service unavailable")
    
    # Risk scoring logic (simplified)
    risk_score = 0.0
    
    # Amount-based risk
    if payment.amount > 100000:  # > 100k NGN
        risk_score += 0.3
    elif payment.amount > 50000:  # > 50k NGN
        risk_score += 0.2
    
    # Method-based risk
    if payment.method == PaymentMethod.CARD:
        risk_score += 0.1
    
    # Add some randomness
    risk_score += random.uniform(0, 0.2)
    
    # Log fraud check
    logger.info("fraud_check_completed", 
                customer_id=payment.customer_id,
                amount=payment.amount,
                risk_score=risk_score)
    
    if risk_score > 0.7:
        FRAUD_DETECTIONS.labels(risk_level="high").inc()
    elif risk_score > 0.4:
        FRAUD_DETECTIONS.labels(risk_level="medium").inc()
    else:
        FRAUD_DETECTIONS.labels(risk_level="low").inc()
    
    return min(risk_score, 1.0)

async def process_payment_async(transaction_id: str, payment: PaymentRequest):
    """Background payment processing with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            ACTIVE_PAYMENTS.inc()
            
            # Get current payment state
            payment_record = payments_db.get(transaction_id)
            if not payment_record:
                logger.error("payment_not_found", transaction_id=transaction_id)
                return
            
            # Update status to processing
            payment_record.status = PaymentStatus.PROCESSING
            payments_db[transaction_id] = payment_record
            
            logger.info("payment_processing_started", 
                       transaction_id=transaction_id,
                       attempt=attempt + 1)
            
            # Simulate payment processing time
            processing_time = random.uniform(2, 8)
            await asyncio.sleep(processing_time)
            
            # Simulate payment success/failure
            if random.random() < 0.95:  # 95% success rate
                payment_record.status = PaymentStatus.COMPLETED
                PAYMENT_REQUESTS.labels(method=payment.method.value, status="completed").inc()
                logger.info("payment_completed", 
                           transaction_id=transaction_id,
                           processing_time=processing_time)
            else:
                payment_record.status = PaymentStatus.FAILED
                PAYMENT_REQUESTS.labels(method=payment.method.value, status="failed").inc()
                logger.error("payment_failed", 
                            transaction_id=transaction_id,
                            reason="processing_error")
            
            payments_db[transaction_id] = payment_record
            ACTIVE_PAYMENTS.dec()
            return
            
        except Exception as e:
            logger.error("payment_processing_error", 
                        transaction_id=transaction_id,
                        attempt=attempt + 1,
                        error=str(e))
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                # Final failure
                payment_record = payments_db.get(transaction_id)
                if payment_record:
                    payment_record.status = PaymentStatus.FAILED
                    payments_db[transaction_id] = payment_record
                PAYMENT_REQUESTS.labels(method=payment.method.value, status="failed").inc()
                ACTIVE_PAYMENTS.dec()

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint with detailed service status"""
    uptime = time.time() - start_time
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
        uptime_seconds=uptime
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

@app.post("/payments", response_model=PaymentResponse)
async def create_payment(payment: PaymentRequest, background_tasks: BackgroundTasks):
    """Create a new payment with fraud detection and risk assessment"""
    
    with PAYMENT_LATENCY.time():
        transaction_id = str(uuid.uuid4())
        
        logger.info("payment_request_received", 
                   transaction_id=transaction_id,
                   customer_id=payment.customer_id,
                   amount=payment.amount,
                   method=payment.method.value)
        
        try:
            # Fraud check with circuit breaker
            risk_score = await fraud_service_cb.call(check_fraud_risk, payment)
            
            # Determine initial status based on risk
            initial_status = PaymentStatus.PENDING
            if risk_score > 0.8:
                initial_status = PaymentStatus.FRAUD_DETECTED
                PAYMENT_REQUESTS.labels(method=payment.method.value, status="fraud_detected").inc()
                logger.warning("high_risk_payment_blocked", 
                              transaction_id=transaction_id,
                              risk_score=risk_score)
            else:
                PAYMENT_REQUESTS.labels(method=payment.method.value, status="pending").inc()
            
            # Record payment amount for monitoring
            PAYMENT_AMOUNT.observe(payment.amount)
            
            # Create payment record
            payment_response = PaymentResponse(
                transaction_id=transaction_id,
                status=initial_status,
                amount=payment.amount,
                currency=payment.currency,
                method=payment.method,
                created_at=datetime.now(timezone.utc),
                estimated_completion=datetime.now(timezone.utc) if initial_status == PaymentStatus.FRAUD_DETECTED else None,
                risk_score=risk_score
            )
            
            payments_db[transaction_id] = payment_response
            
            # Start background processing if not blocked
            if initial_status != PaymentStatus.FRAUD_DETECTED:
                background_tasks.add_task(process_payment_async, transaction_id, payment)
            
            return payment_response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("payment_creation_failed", 
                        transaction_id=transaction_id,
                        error=str(e))
            PAYMENT_REQUESTS.labels(method=payment.method.value, status="error").inc()
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/payments/{transaction_id}", response_model=PaymentResponse)
async def get_payment(transaction_id: str):
    """Get payment status by transaction ID"""
    
    logger.info("payment_status_requested", transaction_id=transaction_id)
    
    payment = payments_db.get(transaction_id)
    if not payment:
        logger.warning("payment_not_found", transaction_id=transaction_id)
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment

@app.get("/payments")
async def list_payments(
    customer_id: Optional[str] = None,
    status: Optional[PaymentStatus] = None,
    limit: int = 10
):
    """List payments with optional filtering"""
    
    payments = list(payments_db.values())
    
    # Apply filters
    if customer_id:
        # Note: In a real implementation, you'd store customer_id in the payment record
        pass
    
    if status:
        payments = [p for p in payments if p.status == status]
    
    # Sort by creation time (newest first) and limit
    payments.sort(key=lambda x: x.created_at, reverse=True)
    payments = payments[:limit]
    
    logger.info("payments_listed", count=len(payments), filters={
        "customer_id": customer_id,
        "status": status.value if status else None
    })
    
    return {"payments": payments, "total": len(payments)}

if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8001)
    logger.info("payment_service_starting", metrics_port=8001)
    
    # Start FastAPI application
    uvicorn.run(app, host="0.0.0.0", port=8000)
