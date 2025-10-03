#!/usr/bin/env python3
"""
Deployment Health Check Script
Monitors key metrics and health indicators after deployment
"""

import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    import json
except ImportError:
    pass  # json is built-in


def check_service_health(base_url="http://localhost:8000"):
    """Check if the payment service is healthy"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Payment service health check passed")
            return True
        else:
            print(f"❌ Payment service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Payment service health check error: {e}")
        return False


def check_metrics_availability(base_url="http://localhost:8000"):
    """Check if metrics are being exposed properly"""
    try:
        response = requests.get(f"{base_url}/metrics", timeout=10)
        if response.status_code == 200:
            metrics_text = response.text
            
            # Check for essential metrics
            essential_metrics = [
                "python_info",
                "process_cpu_seconds_total",
                "http_requests_total"
            ]
            
            found_metrics = []
            for metric in essential_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)
            
            print(f"✅ Metrics endpoint accessible, found {len(found_metrics)}/{len(essential_metrics)} essential metrics")
            return True
        else:
            print(f"❌ Metrics endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Metrics check error: {e}")
        return False


def check_prometheus_targets(prometheus_url="http://localhost:9090"):
    """Check Prometheus target health"""
    try:
        response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=10)
        if response.status_code == 200:
            targets = response.json()
            
            active_targets = targets.get('data', {}).get('activeTargets', [])
            healthy_targets = [t for t in active_targets if t.get('health') == 'up']
            
            print(f"✅ Prometheus targets: {len(healthy_targets)}/{len(active_targets)} healthy")
            
            if len(healthy_targets) < len(active_targets):
                print("⚠️  Some targets are down:")
                for target in active_targets:
                    if target.get('health') != 'up':
                        print(f"  - {target.get('job', 'unknown')}: {target.get('health', 'unknown')}")
            
            return len(healthy_targets) > 0
        else:
            print(f"❌ Prometheus API failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Prometheus check error: {e}")
        return False


def check_response_times(base_url="http://localhost:8000", samples=10):
    """Check average response times"""
    print(f"📊 Checking response times ({samples} samples)...")
    
    times = []
    successful = 0
    
    for i in range(samples):
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}/health", timeout=5)
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = end_time - start_time
                times.append(response_time)
                successful += 1
            
        except Exception:
            pass
        
        time.sleep(0.1)  # Brief pause between requests
    
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"✅ Response times - Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")
        print(f"✅ Success rate: {successful}/{samples} ({successful/samples*100:.1f}%)")
        
        # Alert thresholds
        if avg_time > 1.0:
            print("⚠️  High average response time detected!")
            return False
        
        if successful < samples * 0.95:  # Less than 95% success rate
            print("⚠️  Low success rate detected!")
            return False
        
        return True
    else:
        print("❌ No successful requests")
        return False


def main():
    """Main health check routine"""
    print(f"🔍 Starting deployment health check at {datetime.now()}")
    print("=" * 50)
    
    checks = []
    
    # Service health check
    checks.append(check_service_health())
    
    # Metrics availability
    checks.append(check_metrics_availability())
    
    # Prometheus health
    checks.append(check_prometheus_targets())
    
    # Response time check
    checks.append(check_response_times())
    
    print("=" * 50)
    
    passed_checks = sum(checks)
    total_checks = len(checks)
    
    print(f"📊 Health check summary: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 All health checks passed! Deployment is healthy.")
        sys.exit(0)
    else:
        print("❌ Some health checks failed! Manual investigation required.")
        sys.exit(1)


if __name__ == "__main__":
    main()
