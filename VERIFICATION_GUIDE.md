# Resilient Analytics API - Verification Guide

This guide provides step-by-step commands to verify all core requirements of the Resilient Analytics API task.

## Prerequisites

Ensure you have the following installed:
- Docker Desktop (running)
- Git Bash
- curl (comes with Git Bash)
- jq (optional, for JSON formatting)

---

## 🚀 **STEP 1: Clone and Navigate to Project**

```bash
# If not already in the project directory
cd /c/Users/asruj/resilient-analytics-api

# Verify project structure
ls -la

# Check key files exist
ls Dockerfile docker-compose.yml README.md requirements.txt
ls -R src/ tests/
```

**Expected Output**: All files and directories should be present.

---

## 🐳 **STEP 2: Build and Start Docker Containers**

```bash
# Stop any existing containers
docker-compose down -v

# Build and start services
docker-compose up --build -d

# Wait for services to be healthy (30-60 seconds)
sleep 30

# Check container status
docker-compose ps

# Verify both services are "healthy"
docker-compose ps | grep -E "(healthy|Up)"
```

**Expected Output**: 
- `resilient-api-app` should show "healthy"
- `resilient-api-redis` should show "healthy"

```bash
# Check application logs
docker-compose logs app | tail -20

# Check Redis logs
docker-compose logs redis | tail -10
```

---

## 🏥 **STEP 3: Verify Health Endpoint**

```bash
# Test health endpoint
curl -s http://localhost:8000/health | jq .

# Alternative without jq
curl -s http://localhost:8000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-20T...",
  "redis_connection": "connected",
  "version": "1.0.0"
}
```

---

## 📝 **STEP 4: Test POST /api/metrics (Requirement 1)**

### 4.1 Post Valid Metrics

```bash
# Post metric #1
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T10:00:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  }'

# Post metric #2
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T10:05:00Z",
    "value": 82.3,
    "type": "cpu_usage"
  }'

# Post metric #3
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T10:10:00Z",
    "value": 68.1,
    "type": "cpu_usage"
  }'

# Post different type
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T10:00:00Z",
    "value": 1024.5,
    "type": "memory_usage"
  }'
```

**Expected Output**: Each should return `201 Created` with a success message.

### 4.2 Test Invalid Payloads

```bash
# Missing field
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-02-20T10:00:00Z", "value": 75.5}'

# Invalid timestamp
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "invalid-date",
    "value": 75.5,
    "type": "cpu_usage"
  }'

# Invalid value type
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T10:00:00Z",
    "value": "not-a-number",
    "type": "cpu_usage"
  }'
```

**Expected Output**: Each should return `400 Bad Request` or `422 Unprocessable Entity`.

---

## 📊 **STEP 5: Test GET /api/metrics/summary (Requirement 2)**

```bash
# Get summary for cpu_usage
curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly" | jq .

# Get summary for memory_usage
curl -s "http://localhost:8000/api/metrics/summary?type=memory_usage&period=daily" | jq .

# Without jq
curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly"
```

**Expected Output**:
```json
{
  "type": "cpu_usage",
  "period": "hourly",
  "average_value": 75.3,
  "count": 3,
  "min_value": 68.1,
  "max_value": 82.3
}
```

---

## 💾 **STEP 6: Test Redis Caching (Requirements 3-4)**

### 6.1 Verify Cache Miss and Cache Hit

```bash
# First request (cache miss - slower)
echo "Request 1 (Cache Miss):"
time curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly" | jq .

# Second request (cache hit - faster)
echo "Request 2 (Cache Hit):"
time curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly" | jq .

# Third request (cache hit - faster)
echo "Request 3 (Cache Hit):"
time curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly" | jq .
```

**Expected Behavior**: 
- First request slower (computing)
- Subsequent requests faster (from cache)
- Check logs: `docker-compose logs app | grep -i cache`

### 6.2 Verify Cache in Redis

```bash
# Access Redis CLI
docker exec -it resilient-api-redis redis-cli

# Inside Redis CLI, run:
# KEYS *
# GET summary:cpu_usage:hourly
# TTL summary:cpu_usage:hourly
# EXIT
```

**Or from command line:**

```bash
# Check Redis keys
docker exec resilient-api-redis redis-cli KEYS "*"

# Check specific cache key
docker exec resilient-api-redis redis-cli GET "summary:cpu_usage:hourly"

# Check TTL (Time To Live)
docker exec resilient-api-redis redis-cli TTL "summary:cpu_usage:hourly"
```

**Expected Output**: 
- Keys exist with pattern `summary:*`
- TTL shows remaining seconds (e.g., 290 out of 300)

### 6.3 Test Cache Expiration

```bash
# Note the current cache TTL
docker exec resilient-api-redis redis-cli TTL "summary:cpu_usage:hourly"

# Wait for cache to expire (or set a shorter TTL in .env)
# Check application logs for cache behavior
docker-compose logs app | grep -E "(cache|Cache)" | tail -20
```

---

## 🚦 **STEP 7: Test Rate Limiting (Requirements 5-6)**

### 7.1 Normal Requests Within Limit

```bash
# Make requests within the limit (10 req/min by default)
for i in {1..5}; do
  echo "Request $i:"
  curl -s -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{
      \"timestamp\": \"2026-02-20T10:$(printf '%02d' $i):00Z\",
      \"value\": $((70 + i)),
      \"type\": \"cpu_usage\"
    }" | jq .
  sleep 0.5
done
```

**Expected Output**: All requests should return `201 Created`.

### 7.2 Exceed Rate Limit

```bash
# Rapidly send requests to exceed limit (>10 requests)
echo "Testing rate limit..."
for i in {1..15}; do
  echo "Request $i:"
  response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{
      \"timestamp\": \"2026-02-20T11:$(printf '%02d' $i):00Z\",
      \"value\": $((70 + i)),
      \"type\": \"cpu_usage\"
    }")
  
  echo "$response"
  echo "---"
done
```

**Expected Behavior**:
- First 10 requests: `201 Created`
- Subsequent requests: `429 Too Many Requests`
- Response should include `Retry-After` header

### 7.3 Check Retry-After Header

```bash
# Send request to trigger rate limit and check headers
curl -v -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T12:00:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  }' 2>&1 | grep -i "retry-after"
```

**Expected Output**: Should show `Retry-After: <seconds>` header.

### 7.4 Verify Rate Limit in Redis

```bash
# Check rate limit keys in Redis
docker exec resilient-api-redis redis-cli KEYS "rate_limit:*"

# Check specific rate limit counter
docker exec resilient-api-redis redis-cli GET "rate_limit:127.0.0.1"

# Check TTL
docker exec resilient-api-redis redis-cli TTL "rate_limit:127.0.0.1"
```

### 7.5 Wait and Retry After Limit Reset

```bash
# Wait for rate limit window to reset (60 seconds)
echo "Waiting 65 seconds for rate limit reset..."
sleep 65

# Try posting again
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-20T12:30:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  }'
```

**Expected Output**: Should return `201 Created` again.

---

## ⚡ **STEP 8: Test Circuit Breaker (Requirements 7-11)**

The circuit breaker is tested through the external service endpoint.

### 8.1 Test Circuit Breaker - Closed State (Normal)

```bash
# Call external service endpoint multiple times
echo "Testing Circuit Breaker in CLOSED state..."
for i in {1..3}; do
  echo "Request $i:"
  curl -s http://localhost:8000/api/external | jq .
  sleep 1
done
```

**Expected Output**: Most requests should succeed (90% success rate by default).

### 8.2 Force Circuit to OPEN State

First, temporarily increase failure rate:

```bash
# Stop containers
docker-compose down

# Edit docker-compose.yml or create .env file with:
# EXTERNAL_SERVICE_FAILURE_RATE=1.0

# Or modify docker-compose.yml directly
# Set EXTERNAL_SERVICE_FAILURE_RATE=1.0 in app environment

# Restart
docker-compose up -d

# Wait for healthy
sleep 30
```

**Alternative: Use environment variable override**

```bash
# Stop services
docker-compose down

# Start with high failure rate
EXTERNAL_SERVICE_FAILURE_RATE=0.9 docker-compose up -d

# Wait for ready
sleep 30
```

Now trigger failures:

```bash
# Make requests to trigger circuit breaker (need 5 failures by default)
echo "Triggering circuit breaker failures..."
for i in {1..8}; do
  echo "Request $i:"
  response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" http://localhost:8000/api/external)
  echo "$response"
  echo "---"
  sleep 1
done
```

**Expected Behavior**:
- First 5 failures trigger circuit to OPEN
- Subsequent requests immediately return fallback without calling external service (fail fast)
- Status code should be `503 Service Unavailable` when circuit is open

### 8.3 Verify Circuit State in Logs

```bash
# Check circuit breaker state changes in logs
docker-compose logs app | grep -i "circuit"

# Look for messages like:
# "Circuit breaker opened"
# "Circuit breaker attempting half-open"
# "Circuit breaker closed"
```

### 8.4 Test Half-Open State

```bash
# Wait for reset timeout (30 seconds by default)
echo "Waiting for circuit breaker reset timeout (35 seconds)..."
sleep 35

# Make a request - should attempt half-open
echo "Testing HALF-OPEN state:"
curl -s http://localhost:8000/api/external | jq .

# Check logs
docker-compose logs app | grep -i "half-open"
```

### 8.5 Test Circuit Recovery

```bash
# Reset failure rate to low
docker-compose down

# Remove environment override or reset to 0.1
docker-compose up -d

# Wait for healthy
sleep 30

# Make requests to close circuit
echo "Testing circuit recovery..."
for i in {1..5}; do
  echo "Request $i:"
  curl -s http://localhost:8000/api/external | jq .
  sleep 2
done

# Check circuit state
docker-compose logs app | grep -i "circuit" | tail -10
```

**Expected Behavior**: Circuit should close after successful requests in half-open state.

---

## 🧪 **STEP 9: Run Automated Tests (Requirement 14)**

### 9.1 Run All Tests

```bash
# Run tests inside the container
docker-compose exec app pytest tests/ -v

# Or run with coverage
docker-compose exec app pytest tests/ -v --cov=src --cov-report=term-missing
```

**Expected Output**: All tests should pass.

### 9.2 Run Specific Test Files

```bash
# Test rate limiter
docker-compose exec app pytest tests/test_rate_limiter.py -v

# Test circuit breaker
docker-compose exec app pytest tests/test_circuit_breaker.py -v

# Test cache service
docker-compose exec app pytest tests/test_cache_service.py -v

# Test API integration
docker-compose exec app pytest tests/test_api_integration.py -v
```

### 9.3 Check Test Coverage

```bash
# Generate coverage report
docker-compose exec app pytest tests/ --cov=src --cov-report=html

# Coverage files will be in htmlcov/ directory
```

---

## 📚 **STEP 10: Verify Documentation (Requirement 15)**

### 10.1 Check README.md

```bash
# Display README
cat README.md | head -100

# Check for required sections:
grep -E "^##" README.md
```

**Expected Sections**:
- Overview
- Setup Instructions
- API Documentation
- Architecture
- Testing Instructions

### 10.2 Check API Documentation

```bash
# Check API_DOCS.md
ls API_DOCS.md

# View API docs
cat API_DOCS.md | head -50

# Or check OpenAPI/Swagger docs
curl -s http://localhost:8000/docs
# Should redirect to Swagger UI
```

### 10.3 Check Other Documentation

```bash
# Check architecture documentation
ls ARCHITECTURE.md
cat ARCHITECTURE.md | head -50

# Check testing guide
ls TESTING_GUIDE.md
cat TESTING_GUIDE.md | head -50

# Check project summary
ls PROJECT_SUMMARY.md
```

---

## 🔍 **STEP 11: Verify Docker Configuration (Requirements 12-13)**

### 11.1 Check Dockerfile

```bash
# View Dockerfile
cat Dockerfile

# Verify multi-stage build or optimization
grep -E "FROM|COPY|RUN|CMD" Dockerfile
```

### 11.2 Check docker-compose.yml

```bash
# View docker-compose configuration
cat docker-compose.yml

# Check health checks exist
grep -A 4 "healthcheck:" docker-compose.yml

# Check environment variables
grep -A 15 "environment:" docker-compose.yml
```

**Expected**: Both `app` and `redis` services should have healthcheck configurations.

### 11.3 Check Environment Variables

```bash
# Check .env.example exists
ls .env.example

# View environment variables
cat .env.example
```

---

## 🎯 **STEP 12: Complete Integration Test**

Run a comprehensive end-to-end test:

```bash
# Create a test script
cat > test_complete.sh << 'EOF'
#!/bin/bash

echo "=== COMPLETE INTEGRATION TEST ==="
echo ""

echo "1. Health Check..."
curl -s http://localhost:8000/health | jq -r '.status'

echo ""
echo "2. Post Metrics..."
for i in {1..3}; do
  curl -s -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{\"timestamp\": \"2026-02-20T14:0$i:00Z\", \"value\": $((70 + i)), \"type\": \"test_metric\"}" \
    | jq -r '.message'
done

echo ""
echo "3. Get Summary (Cache Miss)..."
curl -s "http://localhost:8000/api/metrics/summary?type=test_metric&period=hourly" | jq .

echo ""
echo "4. Get Summary (Cache Hit)..."
curl -s "http://localhost:8000/api/metrics/summary?type=test_metric&period=hourly" | jq .

echo ""
echo "5. Test Rate Limit..."
for i in {1..12}; do
  response=$(curl -s -w "%{http_code}" -o /dev/null \
    -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{\"timestamp\": \"2026-02-20T15:$i:00Z\", \"value\": 75, \"type\": \"test\"}")
  echo "Request $i: HTTP $response"
done

echo ""
echo "6. Test Circuit Breaker..."
for i in {1..3}; do
  response=$(curl -s http://localhost:8000/api/external | jq -r '.source')
  echo "External call $i: $response"
  sleep 1
done

echo ""
echo "=== TEST COMPLETE ==="
EOF

chmod +x test_complete.sh
./test_complete.sh
```

---

## 📋 **STEP 13: Final Verification Checklist**

Use this checklist to ensure all requirements are met:

```bash
cat << 'EOF'
CORE REQUIREMENTS CHECKLIST:
============================

[✓] 1. POST /api/metrics accepts timestamp, value, type payload
[✓] 2. GET /api/metrics/summary returns aggregated metrics
[✓] 3. Redis-backed caching layer implemented with TTL
[✓] 4. Cached data served for repeated requests
[✓] 5. Global rate limit enforced via Redis (10 req/min/IP)
[✓] 6. Rate-limited requests return 429 with Retry-After header
[✓] 7. Circuit breaker protects external service calls
[✓] 8. Circuit opens after failure threshold (5 failures)
[✓] 9. Open circuit returns predefined fallback immediately
[✓] 10. Circuit transitions to half-open after timeout (30s)
[✓] 11. Successful half-open test closes circuit
[✓] 12. Application and Redis containerized with Docker
[✓] 13. docker-compose.yml includes health checks
[✓] 14. Automated unit and integration tests included
[✓] 15. README.md provides complete documentation

VERIFICATION COMMANDS:
======================

# Check all containers are healthy
docker-compose ps

# Check all tests pass
docker-compose exec app pytest tests/ -v

# Check API endpoints work
curl http://localhost:8000/health
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly"

# Check Redis caching
docker exec resilient-api-redis redis-cli KEYS "*"

# Check logs for circuit breaker
docker-compose logs app | grep -i circuit

EOF
```

---

## 🛑 **STEP 14: Cleanup**

When verification is complete:

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (clears Redis data)
docker-compose down -v

# Remove images (optional)
docker-compose down --rmi all -v
```

---

## 📊 **Summary: Quick Verification Commands**

For a quick check, run these commands in sequence:

```bash
# 1. Start services
docker-compose up -d && sleep 30

# 2. Check health
curl -s http://localhost:8000/health | jq .

# 3. Post metrics
curl -X POST http://localhost:8000/api/metrics -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-02-20T10:00:00Z", "value": 75.5, "type": "cpu_usage"}'

# 4. Get summary
curl -s "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly" | jq .

# 5. Verify caching
docker exec resilient-api-redis redis-cli KEYS "*"

# 6. Run tests
docker-compose exec app pytest tests/ -v

# 7. Check rate limit
for i in {1..12}; do curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d "{\"timestamp\": \"2026-02-20T11:0$i:00Z\", \"value\": 75, \"type\": \"test\"}"; done

# 8. Test circuit breaker
for i in {1..5}; do curl -s http://localhost:8000/api/external | jq .; sleep 1; done

# 9. Check logs
docker-compose logs app | tail -50

# 10. Verify documentation
ls README.md API_DOCS.md ARCHITECTURE.md TESTING_GUIDE.md
```

---

## 🎓 **Expected Results Summary**

| Requirement | Test Command | Expected Result |
|------------|--------------|-----------------|
| POST metrics | `curl -X POST .../api/metrics` | 201 Created |
| GET summary | `curl .../api/metrics/summary` | 200 OK with aggregated data |
| Redis caching | `docker exec ... redis-cli KEYS "*"` | Cache keys present |
| Rate limiting | 12+ rapid POST requests | First 10 succeed, rest return 429 |
| Retry-After | Rate limit response headers | `Retry-After: <seconds>` present |
| Circuit breaker | Multiple external calls | Opens after 5 failures |
| Fallback response | Call when circuit open | 503 with fallback data |
| Half-open state | Wait 30s after open | Single test request attempted |
| Health checks | `docker-compose ps` | Both services show "healthy" |
| Tests | `pytest tests/ -v` | All tests pass |
| Documentation | `ls *.md` | All required docs present |

---

## ❓ Troubleshooting

### Services not starting:
```bash
docker-compose logs
docker-compose ps
```

### Redis connection issues:
```bash
docker exec resilient-api-redis redis-cli ping
```

### Application errors:
```bash
docker-compose logs app | tail -100
```

### Port already in use:
```bash
# Check what's using port 8000
netstat -ano | findstr :8000

# Change port in docker-compose.yml or kill the process
```

### Tests failing:
```bash
# Check test output
docker-compose exec app pytest tests/ -v -s

# Check Redis is accessible from app
docker-compose exec app python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"
```

---

## ✅ **Submission Verification**

Before submitting, ensure:

1. ✅ All 15 core requirements are met
2. ✅ All automated tests pass
3. ✅ Documentation is complete and accurate
4. ✅ Docker containers build and run successfully
5. ✅ API endpoints respond correctly
6. ✅ Health checks are configured and passing
7. ✅ Environment variables are documented in .env.example
8. ✅ README.md has setup and run instructions
9. ✅ Code is well-commented and follows best practices
10. ✅ Repository is public and accessible on GitHub

---

**Good luck with your submission! 🚀**
