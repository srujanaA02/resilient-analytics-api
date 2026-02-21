# Resilient Analytics API

A backend API for real-time analytics with Redis caching, rate limiting, and a circuit breaker for resilient external calls.

## What This Project Provides

- Redis-backed caching for summary requests with configurable TTL
- Per-IP rate limiting on metric ingestion (429 with Retry-After)
- Circuit breaker state machine (closed, open, half-open)
- Dockerized app and Redis with health checks
- Unit and integration test suite

## Quick Start (Docker)

### 1) Clone

```bash
git clone https://github.com/srujanaA02/resilient-analytics-api
cd resilient-analytics-api
```

### 2) Run

```bash
docker-compose up -d --build
```

### 3) Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "redis_connected": true,
  "timestamp": "2026-02-19T12:00:00Z"
}
```

### 4) Stop

```bash
docker-compose down -v
```

## Local Setup (No Docker for App)

### 1) Clone

```bash
git clone https://github.com/srujanaA02/resilient-analytics-api
cd resilient-analytics-api
```

### 2) Create and Activate venv

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3) Install Dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure Environment

```bash
cp .env.example .env
```

### 5) Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 6) Run the API

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Overview

Base URL:

```
http://localhost:8000
```

Endpoints:

- `GET /health`
- `POST /api/metrics`
- `GET /api/metrics/summary?type={type}&period={period}`
- `GET /api/metrics/list?type={type}&limit={limit}`
- `GET /api/circuit-breaker/status`

### Example: Create a Metric

```bash
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-19T12:00:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  }'
```

### Example: Get Summary (Cached)

```bash
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=all"
```

## Testing

Run tests locally:

```bash
pytest
```

Run tests in Docker:

```bash
docker-compose run --rm app pytest
```

## Configuration

All settings are managed via environment variables. See `.env.example` for defaults.

Common settings:

- `CACHE_TTL_SECONDS`
- `RATE_LIMIT_REQUESTS`
- `RATE_LIMIT_WINDOW_SECONDS`
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`
- `CIRCUIT_BREAKER_RESET_TIMEOUT`
- `EXTERNAL_SERVICE_FAILURE_RATE`

## Documentation

- [API_DOCS.md](API_DOCS.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)

## Notes

- The metrics store is in-memory for simplicity.
- Redis is required for caching and rate limiting.

**Last Updated**: February 21, 2026
