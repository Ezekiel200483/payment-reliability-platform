// k6 Load Testing Script for Payment Service
// This script simulates realistic payment processing load for SRE validation

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics for financial SLIs
const paymentSuccessRate = new Rate('payment_success_rate');
const paymentLatency = new Trend('payment_latency', true);
const highValuePayments = new Counter('high_value_payments');
const fraudDetections = new Counter('fraud_detections');

// Test configuration
export const options = {
  stages: [
    // Ramp up
    { duration: '2m', target: 10 },   // Warm up
    { duration: '5m', target: 50 },   // Normal load
    { duration: '10m', target: 100 }, // Peak load
    { duration: '5m', target: 200 },  // Stress test
    { duration: '5m', target: 100 },  // Scale down
    { duration: '2m', target: 0 },    // Cool down
  ],
  
  thresholds: {
    // SRE SLIs/SLOs for payment processing
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // Latency SLO: 95% < 500ms, 99% < 1s
    http_req_failed: ['rate<0.01'],                 // Error rate SLO: < 1%
    payment_success_rate: ['rate>0.99'],           // Payment success SLO: > 99%
    payment_latency: ['p(95)<500'],                // Business latency SLO
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data generators
function generateCustomerId() {
  return `customer_${Math.floor(Math.random() * 10000)}`;
}

function generateMerchantId() {
  const merchants = ['merchant_grocery', 'merchant_gas', 'merchant_restaurant', 'merchant_retail'];
  return merchants[Math.floor(Math.random() * merchants.length)];
}

function generatePaymentAmount() {
  // Realistic Nigerian payment distribution
  const rand = Math.random();
  if (rand < 0.6) return Math.floor(Math.random() * 5000) + 100;      // Small: 100-5000 NGN (60%)
  if (rand < 0.85) return Math.floor(Math.random() * 45000) + 5000;   // Medium: 5k-50k NGN (25%)
  if (rand < 0.95) return Math.floor(Math.random() * 450000) + 50000; // Large: 50k-500k NGN (10%)
  return Math.floor(Math.random() * 4500000) + 500000;                // Very large: 500k-5M NGN (5%)
}

function generatePaymentMethod() {
  const methods = ['card', 'bank_transfer', 'ussd', 'qr_code'];
  const weights = [0.4, 0.3, 0.2, 0.1]; // Realistic distribution
  
  const rand = Math.random();
  let cumulative = 0;
  
  for (let i = 0; i < methods.length; i++) {
    cumulative += weights[i];
    if (rand <= cumulative) return methods[i];
  }
  
  return methods[0];
}

// Health check test
export function healthCheck() {
  group('Health Check', () => {
    const response = http.get(`${BASE_URL}/health`);
    check(response, {
      'health check status is 200': (r) => r.status === 200,
      'health check response time < 100ms': (r) => r.timings.duration < 100,
      'service is healthy': (r) => JSON.parse(r.body).status === 'healthy',
    });
  });
}

// Main payment processing test
export default function() {
  group('Payment Processing', () => {
    // Generate test payment data
    const paymentData = {
      amount: generatePaymentAmount(),
      currency: 'NGN',
      method: generatePaymentMethod(),
      customer_id: generateCustomerId(),
      merchant_id: generateMerchantId(),
      description: `Test payment ${__VU}-${__ITER}`,
      callback_url: `https://merchant.example.com/callback/${__VU}-${__ITER}`
    };

    // Track high-value payments
    if (paymentData.amount > 100000) {
      highValuePayments.add(1);
    }

    // Create payment request
    const startTime = Date.now();
    const createResponse = http.post(
      `${BASE_URL}/payments`,
      JSON.stringify(paymentData),
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': `load-test-${__VU}-${__ITER}`,
        },
      }
    );

    const paymentLatencyMs = Date.now() - startTime;
    paymentLatency.add(paymentLatencyMs);

    const createSuccess = check(createResponse, {
      'payment creation status is 201 or 200': (r) => [200, 201].includes(r.status),
      'payment creation response time < 1s': (r) => r.timings.duration < 1000,
      'response has transaction_id': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.transaction_id && body.transaction_id.length > 0;
        } catch (e) {
          return false;
        }
      },
    });

    if (createSuccess && createResponse.status < 400) {
      paymentSuccessRate.add(1);
      
      const paymentResponse = JSON.parse(createResponse.body);
      const transactionId = paymentResponse.transaction_id;

      // Track fraud detections
      if (paymentResponse.status === 'fraud_detected') {
        fraudDetections.add(1);
      }

      // Simulate checking payment status (common user behavior)
      sleep(Math.random() * 2); // Random delay 0-2 seconds
      
      const statusResponse = http.get(`${BASE_URL}/payments/${transactionId}`, {
        headers: {
          'X-Request-ID': `status-check-${__VU}-${__ITER}`,
        },
      });

      check(statusResponse, {
        'payment status check is 200': (r) => r.status === 200,
        'payment status response time < 500ms': (r) => r.timings.duration < 500,
        'status response has valid data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.transaction_id === transactionId;
          } catch (e) {
            return false;
          }
        },
      });

    } else {
      paymentSuccessRate.add(0);
    }
  });

  // Realistic user think time
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

// Scenario for testing payment listing endpoint
export function paymentsList() {
  group('Payment List API', () => {
    const listResponse = http.get(`${BASE_URL}/payments?limit=10`, {
      headers: {
        'X-Request-ID': `list-payments-${__VU}-${__ITER}`,
      },
    });

    check(listResponse, {
      'payment list status is 200': (r) => r.status === 200,
      'payment list response time < 300ms': (r) => r.timings.duration < 300,
      'payment list has payments array': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body.payments);
        } catch (e) {
          return false;
        }
      },
    });
  });
}

// Scenario for testing metrics endpoint
export function metricsCheck() {
  group('Metrics Endpoint', () => {
    const metricsResponse = http.get(`${BASE_URL}/metrics`, {
      headers: {
        'Accept': 'text/plain',
      },
    });

    check(metricsResponse, {
      'metrics endpoint status is 200': (r) => r.status === 200,
      'metrics response time < 200ms': (r) => r.timings.duration < 200,
      'metrics contains prometheus format': (r) => r.body.includes('# HELP'),
    });
  });
}

// Setup function - runs once before the test
export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  
  // Verify service is available
  const healthResponse = http.get(`${BASE_URL}/health`);
  if (healthResponse.status !== 200) {
    throw new Error(`Service not healthy: ${healthResponse.status}`);
  }
  
  console.log('Service health check passed, starting load test...');
}

// Teardown function - runs once after the test
export function teardown(data) {
  console.log('Load test completed');
  
  // Could send results to monitoring system here
  // Example: http.post('https://monitoring.company.com/load-test-results', JSON.stringify(data));
}
