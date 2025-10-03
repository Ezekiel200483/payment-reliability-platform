# Payment Service Down Runbook

## 🚨 Alert: PaymentServiceDown

**Severity:** Critical  
**SLA Impact:** Payment processing unavailable  
**Business Impact:** Revenue loss, customer dissatisfaction  

## Immediate Response (0-5 minutes)

### 1. Acknowledge Alert
- [ ] Acknowledge the alert in PagerDuty/monitoring system
- [ ] Post in #incident-response Slack channel
- [ ] Assign incident commander if not already assigned

### 2. Initial Assessment
Check the service health:
```bash
# Check if payment service is responding
curl -f https://api.payment.company.com/health

# Check Kubernetes pod status
kubectl get pods -n payment-service -l app=payment-service

# Check recent deployments
kubectl rollout history deployment/payment-service -n payment-service
```

### 3. Quick Fixes (Try in order)
1. **Restart unhealthy pods:**
   ```bash
   kubectl delete pods -n payment-service -l app=payment-service --field-selector=status.phase!=Running
   ```

2. **Check resource constraints:**
   ```bash
   kubectl top pods -n payment-service
   kubectl describe pods -n payment-service -l app=payment-service
   ```

3. **Rollback if recent deployment:**
   ```bash
   kubectl rollout undo deployment/payment-service -n payment-service
   ```

## Investigation (5-15 minutes)

### Application Logs
```bash
# Check application logs for errors
kubectl logs -f deployment/payment-service -n payment-service --since=15m

# Check for specific error patterns
kubectl logs deployment/payment-service -n payment-service --since=30m | grep -i "error\|exception\|failed"
```

### Infrastructure Health
```bash
# Check node health
kubectl get nodes
kubectl top nodes

# Check cluster events
kubectl get events --sort-by=.metadata.creationTimestamp -n payment-service

# Check ingress/load balancer
kubectl get ingress -n payment-service
kubectl describe ingress payment-service-ingress -n payment-service
```

### Database Connectivity
```bash
# Check database connection from payment service pod
kubectl exec -it deployment/payment-service -n payment-service -- \
  python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://user:pass@host:5432/db')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

### External Dependencies
```bash
# Check Redis connectivity
kubectl exec -it deployment/payment-service -n payment-service -- \
  redis-cli -h redis-service ping

# Check fraud detection service
curl -f https://fraud-api.company.com/health
```

## Common Root Causes & Solutions

### 1. Database Connection Issues
**Symptoms:** Service starts but fails health checks, connection timeout errors

**Solutions:**
- Check database credentials in secrets
- Verify database server is running
- Check network connectivity
- Review connection pool settings

```bash
# Check database server status
kubectl get pods -n database -l app=postgresql

# Check database credentials
kubectl get secret payment-db-credentials -n payment-service -o yaml

# Test database connectivity
kubectl run db-test --rm -i --tty --image=postgres:15 -- \
  psql postgresql://user:pass@host:5432/db -c "SELECT 1;"
```

### 2. Resource Exhaustion
**Symptoms:** Pods stuck in Pending state, OOMKilled status

**Solutions:**
- Scale up resources temporarily
- Check for memory leaks
- Review resource requests/limits

```bash
# Check resource usage
kubectl top pods -n payment-service
kubectl describe node <node-name>

# Temporary scale up
kubectl scale deployment payment-service --replicas=5 -n payment-service

# Update resource limits
kubectl patch deployment payment-service -n payment-service -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "payment-service",
            "resources": {
              "limits": {"memory": "1Gi", "cpu": "1000m"},
              "requests": {"memory": "512Mi", "cpu": "500m"}
            }
          }
        ]
      }
    }
  }
}'
```

### 3. Configuration Issues
**Symptoms:** Service fails to start, configuration errors in logs

**Solutions:**
- Verify ConfigMaps and Secrets
- Check environment variables
- Validate configuration syntax

```bash
# Check ConfigMaps
kubectl get configmap -n payment-service
kubectl describe configmap payment-config -n payment-service

# Check environment variables
kubectl exec deployment/payment-service -n payment-service -- printenv | grep -E "(DATABASE|REDIS|API)"
```

### 4. Network/Ingress Issues
**Symptoms:** External requests failing, internal services working

**Solutions:**
- Check ingress controller
- Verify DNS resolution
- Check load balancer health

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx

# Check load balancer
aws elbv2 describe-load-balancers --names payment-service-alb
aws elbv2 describe-target-health --target-group-arn <target-group-arn>
```

## Recovery Verification (15-20 minutes)

### 1. Health Check Verification
```bash
# Verify service is responding
curl -f https://api.payment.company.com/health

# Check all replicas are healthy
kubectl get pods -n payment-service -l app=payment-service

# Verify readiness probes
kubectl describe pods -n payment-service -l app=payment-service | grep -A5 "Readiness"
```

### 2. Functional Testing
```bash
# Run smoke test
curl -X POST https://api.payment.company.com/payments \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "currency": "NGN", 
    "method": "card",
    "customer_id": "test_customer",
    "merchant_id": "test_merchant"
  }'

# Check metrics endpoint
curl https://api.payment.company.com/metrics | grep payment_requests_total
```

### 3. Monitor Key Metrics
Check Grafana dashboards for:
- [ ] Request rate returning to normal
- [ ] Error rate < 1%
- [ ] Response time < 500ms (p95)
- [ ] Active payment processing resuming

## Post-Incident Actions

### 1. Communication
- [ ] Update incident status in Slack
- [ ] Notify stakeholders of resolution
- [ ] Close PagerDuty incident

### 2. Documentation
- [ ] Update incident timeline
- [ ] Document root cause if identified
- [ ] Note any configuration changes made

### 3. Follow-up
- [ ] Schedule post-mortem meeting within 24 hours
- [ ] Create action items for prevention
- [ ] Update monitoring/alerting if needed

## Escalation

**If service is not recovered within 20 minutes:**
1. Escalate to Lead SRE: @lead-sre
2. Engage Platform Team: @platform-team  
3. Contact Engineering Manager: @eng-manager

**For prolonged outages (>30 minutes):**
1. Engage incident response team
2. Consider activating disaster recovery
3. Prepare customer communication

## Important Notes

- **Never** restart the database during payment processing hours
- **Always** check for active payments before scaling down
- **Document** all commands executed during incident response
- **Preserve** logs and state for post-mortem analysis

## Monitoring Links
- [Payment Service Dashboard](https://grafana.company.com/d/payment-service)
- [Infrastructure Dashboard](https://grafana.company.com/d/infrastructure)
- [Business Metrics Dashboard](https://grafana.company.com/d/business-metrics)
- [Alert Manager](https://alertmanager.company.com)

## Contact Information
- **SRE On-Call:** Check PagerDuty schedule
- **Payment Team Lead:** @payment-lead
- **Infrastructure Team:** @infra-team
- **Security Team:** @security-team (for potential security incidents)
