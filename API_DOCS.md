# API Documentation

## Resilient Analytics API - Detailed API Specification

Version: 1.0.0  
Last Updated: February 19, 2026

## Table of Contents

1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [Rate Limiting](#rate-limiting)
5. [Response Format](#response-format)
6. [Endpoints](#endpoints)
7. [Error Codes](#error-codes)
8. [Examples](#examples)

## Overview

The Resilient Analytics API provides endpoints for ingesting metrics, retrieving aggregated summaries, and monitoring system health. The API implements several resilience patterns including:

- **Redis-backed Caching**: Optimizes repeated queries with configurable TTL
- **Rate Limiting**: Protects endpoints from abuse (10 requests/minute per IP)
- **Circuit Breaker**: Prevents cascading failures from external dependencies

## Base URL

**Local Development:**
```
http://localhost:8000
```

**Docker Container:**
```
http://app:8000
```

## Authentication

Currently, the API does not require authentication. In production, implement OAuth2 or API key authentication.

## Rate Limiting

**Default Limits:**
- **POST /api/metrics**: 10 requests per 60 seconds per client IP
- Other endpoints: No rate limiting

**Rate Limit Headers:**
When rate limited, the API returns:
- Status Code: `429 Too Many Requests`
- Header: `Retry-After: <seconds>` - Time until next request is allowed

**Example Rate Limited Response:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{
  "detail": "Rate limit exceeded"
}
```

## Response Format

All API responses follow a consistent JSON structure.

**Success Response:**
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

**Error Response:**
```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error description",
  "timestamp": "2026-02-19T12:00:00Z"
}
```

## Endpoints

### 1. Health Check

Check API and Redis connectivity status.

**Endpoint:** `GET /health`

**Query Parameters:** None

**Request Headers:** None required

**Response Status Codes:**
- `200 OK` - Service is healthy or degraded
- `500 Internal Server Error` - Service is down

**Response Body:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "timestamp": "2026-02-19T12:00:00.123456"
}
```

**Fields:**
- `status` (string): "healthy" if Redis is connected, "degraded" if not
- `redis_connected` (boolean): Redis connection status
- `timestamp` (string): ISO 8601 timestamp of the health check

**Example Request:**
```bash
curl http://localhost:8000/health
```

---

### 2. Create Metric

Ingest a new metric data point. Subject to rate limiting.

**Endpoint:** `POST /api/metrics`

**Request Headers:**
- `Content-Type: application/json`

**Request Body:**
```json
{
  "timestamp": "2026-02-19T12:00:00Z",
  "value": 75.5,
  "type": "cpu_usage"
}
```

**Fields:**
- `timestamp` (string, required): ISO 8601 formatted timestamp
- `value` (number, required): Numeric metric value
- `type` (string, required): Metric type identifier (1-100 characters)

**Response Status Codes:**
- `201 Created` - Metric successfully ingested
- `400 Bad Request` - Invalid request body
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

**Success Response (201):**
```json
{
  "message": "Metric received",
  "timestamp": "2026-02-19T12:00:01.234567",
  "type": "cpu_usage"
}
```

**Validation Rules:**
- `timestamp` must be valid ISO 8601 format
- `value` must be a valid number (integer or float)
- `type` must be a non-empty string (max 100 characters)

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-19T12:00:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  }'
```

---

### 3. Get Metrics Summary

Retrieve aggregated metrics with caching support (300s TTL).

**Endpoint:** `GET /api/metrics/summary`

**Query Parameters:**
- `type` (string, required): Metric type to summarize
- `period` (string, optional): Time period filter
  - Values: `all`, `daily`, `hourly`
  - Default: `all`

**Request Headers:** None required

**Response Status Codes:**
- `200 OK` - Summary retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `500 Internal Server Error` - Server error

**Response Body:**
```json
{
  "type": "cpu_usage",
  "period": "daily",
  "count": 100,
  "average_value": 75.3,
  "min_value": 10.5,
  "max_value": 95.8,
  "latest_value": 80.2
}
```

**Fields:**
- `type` (string): Metric type summarized
- `period` (string): Time period applied
- `count` (integer): Number of metrics in the summary
- `average_value` (float): Mean value across all metrics
- `min_value` (float): Minimum value found
- `max_value` (float): Maximum value found
- `latest_value` (float): Most recent metric value

**Period Filtering:**
- `all`: Returns all metrics regardless of timestamp
- `daily`: Returns metrics from last 24 hours
- `hourly`: Returns metrics from last 60 minutes

**Caching Behavior:**
- First request computes summary and caches for 300 seconds
- Subsequent requests within TTL served from Redis cache
- Cache key format: `summary:{type}:{period}`

**Empty Result:**
When no metrics match the criteria:
```json
{
  "type": "cpu_usage",
  "period": "daily",
  "count": 0,
  "average_value": 0.0,
  "min_value": 0.0,
  "max_value": 0.0,
  "latest_value": 0.0
}
```

**Example Requests:**
```bash
# Get all cpu_usage metrics
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage"

# Get daily cpu_usage metrics
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=daily"

# Get hourly memory_usage metrics
curl "http://localhost:8000/api/metrics/summary?type=memory_usage&period=hourly"
```

---

### 4. List Metrics

Retrieve a list of individual metrics with optional filtering.

**Endpoint:** `GET /api/metrics/list`

**Query Parameters:**
- `type` (string, optional): Filter by metric type
- `limit` (integer, optional): Maximum number of results
  - Default: 100
  - Range: 1-1000

**Request Headers:** None required

**Response Status Codes:**
- `200 OK` - Metrics retrieved successfully
- `400 Bad Request` - Invalid query parameters
- `500 Internal Server Error` - Server error

**Response Body:**
```json
[
  {
    "id": null,
    "timestamp": "2026-02-19T12:00:00Z",
    "value": 75.5,
    "type": "cpu_usage"
  },
  {
    "id": null,
    "timestamp": "2026-02-19T12:01:00Z",
    "value": 80.2,
    "type": "cpu_usage"
  }
]
```

**Fields:**
- `id` (string|null): Metric identifier (currently always null)
- `timestamp` (string): ISO 8601 timestamp
- `value` (float): Metric value
- `type` (string): Metric type

**Example Requests:**
```bash
# Get last 100 metrics
curl http://localhost:8000/api/metrics/list

# Get last 50 cpu_usage metrics
curl "http://localhost:8000/api/metrics/list?type=cpu_usage&limit=50"

# Get last 10 metrics
curl "http://localhost:8000/api/metrics/list?limit=10"
```

---

### 5. Circuit Breaker Status

Monitor circuit breaker state and failure statistics.

**Endpoint:** `GET /api/circuit-breaker/status`

**Query Parameters:** None

**Request Headers:** None required

**Response Status Codes:**
- `200 OK` - Status retrieved successfully
- `500 Internal Server Error` - Server error

**Response Body:**
```json
{
  "state": "CLOSED",
  "failure_count": 0,
  "success_count": 5
}
```

**Fields:**
- `state` (string): Current circuit breaker state
  - `CLOSED`: Normal operation, requests pass through
  - `OPEN`: Circuit is open, requests immediately fail
  - `HALF_OPEN`: Testing recovery, single test request allowed
- `failure_count` (integer): Number of consecutive failures
- `success_count` (integer): Number of successful requests

**Circuit Breaker State Transitions:**
1. **CLOSED → OPEN**: After 5 consecutive failures
2. **OPEN → HALF_OPEN**: After 30 seconds timeout
3. **HALF_OPEN → CLOSED**: On successful test request
4. **HALF_OPEN → OPEN**: On failed test request

**Example Request:**
```bash
curl http://localhost:8000/api/circuit-breaker/status
```

---

### 6. Root Endpoint

Get basic API information.

**Endpoint:** `GET /`

**Query Parameters:** None

**Request Headers:** None required

**Response Status Codes:**
- `200 OK` - Information retrieved

**Response Body:**
```json
{
  "name": "Resilient Analytics API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

**Example Request:**
```bash
curl http://localhost:8000/
```

---

## Error Codes

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters or body |
| 422 | Unprocessable Entity | Validation error in request body |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Circuit breaker open or service degraded |

### Application Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Request body failed validation |
| RATE_LIMIT_EXCEEDED | Too many requests from client |
| INTERNAL_ERROR | Unexpected server error |
| CIRCUIT_BREAKER_OPEN | External service unavailable |

## Examples

### Example 1: Complete Metric Ingestion Flow

```bash
# 1. Check API health
curl http://localhost:8000/health

# 2. Create multiple metrics
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d "{
      \"timestamp\": \"2026-02-19T12:0$i:00Z\",
      \"value\": $((60 + $i * 5)),
      \"type\": \"cpu_usage\"
    }"
  echo ""
done

# 3. Get summary
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=all"

# 4. Get metrics list
curl "http://localhost:8000/api/metrics/list?type=cpu_usage&limit=10"
```

### Example 2: Testing Rate Limiting

```bash
# Make requests until rate limited
for i in {1..12}; do
  echo "Request $i:"
  curl -i -X POST http://localhost:8000/api/metrics \
    -H "Content-Type: application/json" \
    -d '{
      "timestamp": "2026-02-19T12:00:00Z",
      "value": 75.5,
      "type": "test"
    }'
  echo ""
done

# Observe 429 response on request 11
```

### Example 3: Cache Performance Testing

```bash
# First request (computes and caches)
time curl "http://localhost:8000/api/metrics/summary?type=cpu_usage"

# Second request (served from cache - faster)
time curl "http://localhost:8000/api/metrics/summary?type=cpu_usage"
```

### Example 4: Monitoring Circuit Breaker

```bash
# Check initial state
curl http://localhost:8000/api/circuit-breaker/status

# Make summary requests (triggers external service calls)
for i in {1..5}; do
  curl "http://localhost:8000/api/metrics/summary?type=cpu_usage"
  sleep 1
done

# Check circuit breaker state again
curl http://localhost:8000/api/circuit-breaker/status
```

### Example 5: Period-Based Filtering

```bash
# Create metrics at different times
curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-19T10:00:00Z",
    "value": 60.0,
    "type": "cpu_usage"
  }'

curl -X POST http://localhost:8000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-19T20:00:00Z",
    "value": 80.0,
    "type": "cpu_usage"
  }'

# Get hourly summary (only recent metrics)
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=hourly"

# Get daily summary (all today's metrics)
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=daily"

# Get all-time summary
curl "http://localhost:8000/api/metrics/summary?type=cpu_usage&period=all"
```

## Interactive API Documentation

The API provides interactive documentation using Swagger UI and ReDoc:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to explore and test endpoints directly in your browser.

## Client Libraries

### Python Example

```python
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Create a metric
def create_metric(metric_type, value):
    response = requests.post(
        f"{BASE_URL}/api/metrics",
        json={
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "value": value,
            "type": metric_type
        }
    )
    return response.json()

# Get summary
def get_summary(metric_type, period="all"):
    response = requests.get(
        f"{BASE_URL}/api/metrics/summary",
        params={"type": metric_type, "period": period}
    )
    return response.json()

# Usage
create_metric("cpu_usage", 75.5)
summary = get_summary("cpu_usage", "daily")
print(summary)
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

// Create a metric
async function createMetric(type, value) {
  const response = await axios.post(`${BASE_URL}/api/metrics`, {
    timestamp: new Date().toISOString(),
    value: value,
    type: type
  });
  return response.data;
}

// Get summary
async function getSummary(type, period = 'all') {
  const response = await axios.get(`${BASE_URL}/api/metrics/summary`, {
    params: { type, period }
  });
  return response.data;
}

// Usage
(async () => {
  await createMetric('cpu_usage', 75.5);
  const summary = await getSummary('cpu_usage', 'daily');
  console.log(summary);
})();
```

### cURL Example with Error Handling

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

# Function to create metric with error handling
create_metric() {
  local type=$1
  local value=$2
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  response=$(curl -s -w "\n%{http_code}" -X POST \
    "$BASE_URL/api/metrics" \
    -H "Content-Type: application/json" \
    -d "{
      \"timestamp\": \"$timestamp\",
      \"value\": $value,
      \"type\": \"$type\"
    }")
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" -eq 201 ]; then
    echo "Success: $body"
  elif [ "$http_code" -eq 429 ]; then
    retry_after=$(echo "$body" | grep -oP 'Retry-After: \K\d+')
    echo "Rate limited. Retry after $retry_after seconds"
  else
    echo "Error ($http_code): $body"
  fi
}

# Usage
create_metric "cpu_usage" 75.5
```

## Best Practices

### 1. Handling Rate Limits

```python
import time
import requests

def create_metric_with_retry(metric_type, value, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(
            f"{BASE_URL}/api/metrics",
            json={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "value": value,
                "type": metric_type
            }
        )
        
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
        else:
            raise Exception(f"Error: {response.status_code}")
    
    raise Exception("Max retries exceeded")
```

### 2. Caching Awareness

When making repeated queries, be aware of the 300-second cache TTL:

```python
# First call computes and caches
summary1 = get_summary("cpu_usage", "daily")

# Second call within 300s returns cached result
summary2 = get_summary("cpu_usage", "daily")

# Wait for cache expiration if fresh data is needed
time.sleep(301)
summary3 = get_summary("cpu_usage", "daily")  # Fresh computation
```

### 3. Circuit Breaker Monitoring

Monitor circuit breaker status when making critical requests:

```python
def get_summary_with_circuit_check(metric_type, period="all"):
    # Check circuit breaker status first
    status_response = requests.get(f"{BASE_URL}/api/circuit-breaker/status")
    status = status_response.json()
    
    if status["state"] == "OPEN":
        print("Warning: Circuit breaker is open, using fallback data")
        return {"error": "service_unavailable", "fallback": True}
    
    # Proceed with normal request
    return get_summary(metric_type, period)
```

## Changelog

### Version 1.0.0 (February 19, 2026)
- Initial release
- Core metrics ingestion and retrieval
- Redis-backed caching with 300s TTL
- Rate limiting (10 req/min per IP)
- Circuit breaker pattern for external services
- Health check endpoint
- Comprehensive test coverage

---

**Need Help?**
- GitHub Issues: [Repository Issues](https://github.com/your-repo/issues)
- Documentation: See main README.md
- API Playground: http://localhost:8000/docs
