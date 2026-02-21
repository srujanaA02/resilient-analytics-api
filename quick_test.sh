#!/bin/bash
# Quick verification script for Resilient Analytics API

echo "================================================"
echo "RESILIENT ANALYTICS API - QUICK VERIFICATION"
echo "================================================"
echo ""

sleep 15

echo "✓ Step 1: Health Check"
echo "------------------------"
curl -s http://localhost:8000/health
echo -e "\n"

echo "✓ Step 2: Post Metrics (Requirement 1)"
echo "----------------------------------------"
curl -s -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-02-20T10:00:00Z", "value": 75.5, "type": "cpu_usage"}'
echo ""

curl -s -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-02-20T10:05:00Z", "value": 82.3, "type": "cpu_usage"}'
echo ""

curl -s -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-02-20T10:10:00Z", "value": 68.1, "type": "cpu_usage"}'
echo -e "\n"

echo "✓ Step 3: Get Summary - Cache Miss (Requirement 2-3)"
echo "------------------------------------------------------"
curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly"
echo -e "\n"

echo "✓ Step 4: Get Summary - Cache Hit (Requirement 4)"
echo "---------------------------------------------------"
curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly"
echo -e "\n"

echo "✓ Step 5: Verify Redis Cache (Requirements 3-4)"
echo "-------------------------------------------------"
docker exec resilient-api-redis redis-cli KEYS "*summary*"
docker exec resilient-api-redis redis-cli TTL "summary:cpu_usage:hourly"
echo ""

echo "✓ Step 6: Test Rate Limiting (Requirements 5-6)"
echo "-------------------------------------------------"
echo "Sending 12 rapid requests..."
for i in {1..12}; do
  status=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{\"timestamp\": \"2026-02-20T11:0$i:00Z\", \"value\": 75, \"type\": \"test\"}")
  echo "Request $i: HTTP $status"
done
echo ""

echo "✓ Step 7: Test Circuit Breaker (Requirements 7-11)"
echo "----------------------------------------------------"
for i in {1..5}; do
  echo "External call $i:"
  curl -s http://localhost:8000/api/external
  echo ""
  sleep 1
done
echo ""

echo "✓ Step 8: Circuit Breaker Status"
echo "----------------------------------"
curl -s http://localhost:8000/api/circuit-breaker/status
echo -e "\n"

echo "✓ Step 9: Run Automated Tests (Requirement 14)"
echo "------------------------------------------------"
docker-compose exec -T app pytest tests/ -v --tb=short
echo ""

echo "✓ Step 10: Check Documentation (Requirement 15)"
echo "-------------------------------------------------"
ls -la *.md
echo ""

echo "================================================"
echo "VERIFICATION COMPLETE!"
echo "================================================"
