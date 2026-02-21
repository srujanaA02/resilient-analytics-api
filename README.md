
---

# Resilient Analytics API

A production-ready backend API for real-time analytics featuring:

* Redis-based caching
* Per-IP rate limiting
* Circuit breaker fault tolerance
* Docker containerization with health checks
* Comprehensive unit and integration tests

---

# Table of Contents

1. Overview
2. Project Structure
3. Prerequisites
4. Quick Start (Docker – Recommended)
5. Full System Verification (Step-by-Step)
6. Local Setup (Without Docker for App)
7. API Endpoints
8. Running Tests
9. Configuration
10. Cleanup

---

# 1️⃣ Overview

This project demonstrates resilience patterns required in modern backend systems:

* Cache-aside strategy to reduce computation cost
* Sliding window rate limiting to prevent abuse
* Circuit breaker state machine to isolate external failures
* Containerized deployment with health checks

---

# 2️⃣ Project Structure

```
src/
├── api/
├── services/
├── config/
└── main.py

tests/
├── test_rate_limiter.py
├── test_circuit_breaker.py
├── test_cache_service.py
└── test_api_integration.py

Dockerfile
docker-compose.yml
.env.example
README.md
```

---

# 3️⃣ Prerequisites

* Docker (v20+)
* docker-compose
* Git
* Python 3.11+ (for local development)

---

# 4️⃣ Quick Start (Docker – Recommended)

## Step 1 — Clone Repository

```bash
git clone https://github.com/srujanaA02/resilient-analytics-api
cd resilient-analytics-api
```

---

## Step 2 — Build & Start Services

```bash
docker-compose up -d --build
```

This will:

* Build the FastAPI image
* Install dependencies from requirements.txt
* Start Redis
* Start API service
* Enable health checks

---

## Step 3 — Verify Containers

```bash
docker-compose ps
```

Expected:

```
Up (healthy)
```

---

## Step 4 — Health Check

```bash
curl http://localhost:8000/health
```

Expected:

```json
{
  "status": "healthy",
  "redis_connected": true,
  "timestamp": "2026-02-21T12:00:00Z"
}
```

---

# 5️⃣ Full System Verification (Step-by-Step)

These steps validate every required feature.

---

## STEP 1 — Verify Git History

```bash
git log --oneline | head -10
git log --graph --oneline --all | head -15
```

Confirms clean commit structure.

---

## STEP 2 — Start Docker

```bash
docker-compose up -d --build
docker-compose ps
```

---

## STEP 3 — Health Check

```bash
sleep 3
curl http://localhost:8000/health
curl http://localhost:8000/api/circuit-breaker/status
```

Confirms:

* API running
* Redis connected
* Circuit breaker initialized

---

## STEP 4 — Test Metric Submission

```bash
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-02-21T12:00:00Z","value":85.5,"type":"cpu_usage"}'
```

Expected: `201 Created`

---

## STEP 5 — Test Summary (Caching)

```bash
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage"
```

* First call → computes summary
* Subsequent calls → served from Redis cache

---

## STEP 6 — Test Rate Limiting (10 req/min)

```bash
for i in {1..12}; do 
  curl -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d '{"timestamp":"2026-02-21T12:00:00Z","value":'$i',"type":"rate_test"}' \
    -w "\nRequest $i: HTTP %{http_code}\n"
done
```

Expected:

* First 10 → HTTP 201
* Remaining → HTTP 429

---

## STEP 7 — Verify Stored Metrics

```bash
curl "http://localhost:8000/api/metrics/list?type=rate_test"
```

Should return only successful entries.

---

## STEP 8 — Run Unit Tests

```bash
pytest tests/test_rate_limiter.py -v
pytest tests/test_circuit_breaker.py -v
pytest tests/test_cache_service.py -v
```

All tests should pass.

---

## STEP 9 — Open API Documentation

```bash
curl http://localhost:8000/docs | head -30
```

Or open in browser:

```
http://localhost:8000/docs
```

---

## STEP 10 — Inspect Logs

```bash
docker-compose logs app | tail -20
```

Verify:

* No errors
* Health checks succeeding

---

## STEP 11 — Final Status Check

```bash
docker-compose ps
curl -I http://localhost:8000/health
git log --oneline -n 1
```

Note:
`405 Method Not Allowed` for HEAD request is expected if endpoint only allows GET.

---

# 6️⃣ Local Setup (Without Docker for App)

## Step 1 — Clone

```bash
git clone https://github.com/srujanaA02/resilient-analytics-api
cd resilient-analytics-api
```

---

## Step 2 — Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

Windows:

```
venv\Scripts\activate
```

---

## Step 3 — Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4 — Configure Environment

```bash
cp .env.example .env
```

---

## Step 5 — Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

---

## Step 6 — Run API

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

# 7️⃣ API Endpoints

Base URL:

```
http://localhost:8000
```

Endpoints:

* `GET /health`
* `POST /api/metrics`
* `GET /api/metrics/summary`
* `GET /api/metrics/list`
* `GET /api/circuit-breaker/status`

---

# 8️⃣ Running Tests

Run locally:

```bash
pytest
```

Run inside Docker:

```bash
docker-compose exec app pytest -v
```

---

# 9️⃣ Configuration

Environment variables (see `.env.example`):

* CACHE_TTL_SECONDS
* RATE_LIMIT_REQUESTS
* RATE_LIMIT_WINDOW_SECONDS
* CIRCUIT_BREAKER_FAILURE_THRESHOLD
* CIRCUIT_BREAKER_RESET_TIMEOUT
* EXTERNAL_SERVICE_FAILURE_RATE

---

# 🔟 Cleanup

Stop containers:

```bash
docker-compose down
```

Remove volumes:

```bash
docker-compose down -v
```

---

# Notes

* Metrics storage is in-memory for simplicity.
* Redis is required for caching and rate limiting.
* Circuit breaker protects simulated external service.
* Health checks ensure container readiness.

---
