# Architecture Documentation

## Resilient Analytics API - System Design and Implementation

Version: 1.0.0  
Last Updated: February 19, 2026

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Resilience Mechanisms](#resilience-mechanisms)
6. [Performance Considerations](#performance-considerations)
7. [Scalability](#scalability)
8. [Design Trade-offs](#design-trade-offs)
9. [Future Enhancements](#future-enhancements)

## System Overview

The Resilient Analytics API is designed as a fault-tolerant, high-performance backend service for real-time analytics. The system emphasizes resilience through multiple layers of protection against failures, while maintaining high throughput and low latency.

### Core Architecture Principles

1. **Fault Tolerance**: Multiple failure handling mechanisms prevent cascading failures
2. **Performance**: Caching and efficient data structures minimize latency
3. **Scalability**: Stateless design enables horizontal scaling
4. **Observability**: Structured logging and health checks enable monitoring
5. **Maintainability**: Clean separation of concerns and modular design

### Technology Stack

- **Framework**: FastAPI (Python 3.11+)
  - Chosen for: Async support, automatic validation, built-in docs
- **Cache/State**: Redis 7.x
  - Chosen for: Atomic operations, persistence options, data structures
- **Containerization**: Docker with docker-compose
  - Chosen for: Environment consistency, easy deployment
- **Testing**: pytest with asyncio support
  - Chosen for: Comprehensive async testing, fixtures

## Architecture Patterns

### 1. Layered Architecture

```
┌─────────────────────────────────────────┐
│         API Layer (routes.py)           │
│     FastAPI endpoints, request/response  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Service Layer (services/)          │
│  Rate Limiter, Cache, Circuit Breaker   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│    Infrastructure Layer (Redis)         │
│    Connection pooling, persistence      │
└─────────────────────────────────────────┘
```

**Benefits:**
- Clear separation of concerns
- Easy to test individual layers
- Flexible for future changes

**Implementation:**
- API layer handles HTTP concerns (validation, status codes)
- Service layer contains business logic (caching, rate limiting)
- Infrastructure layer manages external dependencies (Redis)

### 2. Singleton Pattern (Redis Client)

```python
class RedisClient:
    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get(cls) -> redis.Redis:
        if cls._instance is None:
            await cls.initialize()
        return cls._instance
```

**Rationale:**
- Single connection pool across application
- Prevents connection exhaustion
- Efficient resource utilization

**Trade-off:**
- Global state (acceptable for infrastructure components)
- Must ensure proper cleanup on shutdown

### 3. Dependency Injection Pattern

```python
async def get_services():
    redis = await RedisClient.get()
    rate_limiter = RateLimiter(redis)
    cache_service = CacheService(redis)
    circuit_breaker = CircuitBreaker()
    return rate_limiter, cache_service, circuit_breaker
```

**Benefits:**
- Testability (easy to mock dependencies)
- Flexibility (swap implementations)
- Loose coupling

## Component Design

### 1. Rate Limiter

**Algorithm**: Fixed Window Counter with Redis

**Design Choice Rationale:**
- **Fixed Window** chosen over Sliding Window for simplicity
- Redis INCR operation is atomic (thread-safe)
- EXPIRE command handles automatic cleanup

**Implementation:**
```
Client Request → Redis INCR key → Count > Threshold?
                                      ↓ Yes: Reject (429)
                                      ↓ No: Allow + Set TTL if first
```

**State Management:**
- Key format: `rate_limit:{client_ip}`
- Counter expires after window_seconds
- TTL managed by Redis automatically

**Trade-offs:**
- **Pro**: Simple, efficient, atomic operations
- **Con**: Potential burst at window boundaries
- **Alternative Considered**: Sliding window (more complex, marginal benefit)

### 2. Cache Service

**Pattern**: Read-Through Cache with TTL

**Design Choice Rationale:**
- Read-through simplifies API layer code
- TTL prevents stale data accumulation
- Redis SETEX provides atomic set-with-expiry

**Cache Key Structure:**
```
summary:{metric_type}:{period}
```

**Invalidation Strategy:**
- **Time-based (TTL)**: 300 seconds default
- **Manual invalidation**: Not implemented (not required for analytics)
- **Pattern-based cleanup**: Available via clear_pattern()

**Hit/Miss Flow:**
```
Request → Check Cache
            ↓ HIT: Return cached data
            ↓ MISS: Compute → Store in cache → Return
```

**Trade-offs:**
- **Pro**: Significant performance improvement for repeated queries
- **Pro**: Reduces load on compute resources
- **Con**: Potential staleness (acceptable for analytics)
- **Alternative Considered**: Write-through (overkill for this use case)

### 3. Circuit Breaker

**Pattern**: State Machine with Three States

**State Diagram:**
```
           failure_threshold
    CLOSED ─────────────────→ OPEN
       ↑                        │
       │                        │ reset_timeout
       │                        ↓
       └──── success ──── HALF_OPEN
             (test passes)      │
                                │ failure
                                └────→ OPEN
```

**Design Choice Rationale:**
- **State Machine**: Clear, predictable behavior
- **Half-Open State**: Validates service recovery before full restoration
- **Async Lock**: Prevents race conditions in state transitions

**Configuration:**
- `failure_threshold`: 5 failures (balance between sensitivity and stability)
- `reset_timeout`: 30 seconds (allow time for service recovery)

**Failure Detection:**
```python
try:
    result = await external_service()
    record_success()
except Exception:
    record_failure()
    if failure_count >= threshold:
        transition_to_open()
```

**Trade-offs:**
- **Pro**: Prevents cascading failures
- **Pro**: Fast-fail behavior during outages
- **Con**: False positives possible during brief network issues
- **Alternative Considered**: Token bucket (more complex, not needed)

### 4. External Service Simulator

**Purpose**: Controllable failure injection for testing

**Design:**
```python
async def fetch_external_data():
    if random.random() < failure_rate:
        raise RuntimeError("Simulated failure")
    await asyncio.sleep(0.05)  # Simulate latency
    return {"data": "..."}
```

**Features:**
- Configurable failure rate (0.0 - 1.0)
- Simulated network latency
- Runtime adjustable for testing

**Usage in Testing:**
```python
set_failure_rate(1.0)  # Force failures to test circuit breaker
# ... make requests ...
set_failure_rate(0.0)  # Reset to success for recovery testing
```

## Data Flow

### Request Flow: POST /api/metrics

```
1. Client Request
   ↓
2. FastAPI Validation (Pydantic)
   ↓
3. Rate Limiter Check
   ├─ Allowed → Continue
   └─ Blocked → Return 429
   ↓
4. Store in Memory (metrics_db)
   ↓
5. Return 201 Created
```

**Performance Characteristics:**
- Typical latency: 5-10ms (local Redis)
- Bottleneck: Redis network round-trip
- Optimization: Connection pooling

### Request Flow: GET /api/metrics/summary

```
1. Client Request (type=cpu_usage, period=daily)
   ↓
2. Validation (type required, period in valid set)
   ↓
3. Cache Check (key: summary:cpu_usage:daily)
   ├─ HIT → Return cached result (2-5ms)
   └─ MISS → Continue
   ↓
4. Compute Summary (filter + aggregate)
   ↓
5. External Service Call (with Circuit Breaker)
   ├─ Circuit CLOSED → Attempt call
   │   ├─ Success → Record success
   │   └─ Failure → Record failure, increment counter
   ├─ Circuit OPEN → Skip call (fast fail)
   └─ Circuit HALF_OPEN → Test call
   ↓
6. Cache Result (TTL=300s)
   ↓
7. Return Summary
```

**Performance Characteristics:**
- First request: 50-100ms (computation + external call + caching)
- Cached requests: 2-5ms (Redis GET only)
- Circuit open: 10-20ms (computation only, no external call)

## Resilience Mechanisms

### 1. Rate Limiting Protection

**Threat Model:**
- DDoS attacks
- Misconfigured clients
- Accidental loops

**Mitigation:**
- Per-IP rate limiting (10 req/min default)
- Redis-backed (survives app restarts)
- Fail-open on Redis errors (availability > strict limiting)

**Response to Limits:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
```

### 2. Circuit Breaker Protection

**Threat Model:**
- External service outage
- Slow external service (timeout cascade)
- Network issues

**Mitigation:**
- Automatic failure detection
- Fast-fail when open (no resource waste)
- Automatic recovery attempt after timeout

**Behavior During Failure:**
- External call skipped
- Summary still computed from local data
- User receives partial result (no outage)

### 3. Caching Layer

**Threat Model:**
- High read load
- Expensive computations
- External service rate limits

**Mitigation:**
- Redis-backed caching (300s TTL)
- Reduces compute by 80-95% (typical analytics workload)
- Survives app restarts

**Consistency Trade-off:**
- Eventual consistency (300s staleness acceptable)
- Can be reduced via CACHE_TTL_SECONDS env var

### 4. Health Checks

**Purpose**: Orchestrator awareness (Kubernetes, Docker)

**Implementation:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Health Status:**
- "healthy": All systems operational
- "degraded": Redis disconnected (API still functional)

## Performance Considerations

### Async/Await Design

**Rationale:**
- FastAPI uses ASGI (async server gateway)
- Redis client is async (redis.asyncio)
- Maximizes throughput under high concurrency

**Key Async Operations:**
1. Redis operations (all async)
2. External service calls (async)
3. Request handling (async handlers)

**Why Async Matters:**
```
Sync: Request1 → [Redis]→ Request2 → [Redis] → ...
       Total time: n * (latency + processing)

Async: Request1 → [Redis]
       Request2 → [Redis]  } Concurrent
       Request3 → [Redis]
       Total time: max(latency) + processing
```

### Memory Management

**In-Memory Metrics Storage:**
- **Current**: Python list (metrics_db)
- **Trade-off**: Fast access, limited by RAM
- **Production Alternative**: Database (PostgreSQL, InfluxDB)

**Memory Growth:**
- Unbounded growth with current design
- **Mitigation for Production**: 
  - Implement TTL-based expiration
  - Move to persistent database
  - Archive old metrics

### Redis Connection Pooling

**Implementation:**
```python
redis.from_url(
    ...,
    decode_responses=True,
    health_check_interval=30
)
```

**Benefits:**
- Reuses connections across requests
- Health checks detect stale connections
- Automatic reconnection

## Scalability

### Horizontal Scaling

**Current Limitations:**
- In-memory metrics_db (not shared across instances)
- Local circuit breaker state (per-instance)

**Solutions for Scale:**

1. **Shared Storage**
```
Instance1 ─┐
Instance2 ─┼─→ PostgreSQL/MySQL
Instance3 ─┘
```

2. **Distributed Circuit Breaker**
- Store state in Redis
- Use Redis INCR/EXPIRE for counters
- Coordinate across instances

3. **Load Balancer**
```
Client → Load Balancer → Instance1
                       → Instance2
                       → Instance3
```

### Vertical Scaling

**Bottlenecks:**
1. Redis memory (cache + rate limiting)
2. Network bandwidth (Redis connection)
3. CPU (summary computation)

**Mitigation:**
- Redis cluster for memory scaling
- Connection pooling for network efficiency
- Pre-aggregation for CPU reduction

### Redis Scaling

**Current**: Single Redis instance

**Production Options:**

1. **Redis Sentinel** (High Availability)
```
Redis Master ←→ Redis Replica1
             ←→ Redis Replica2
Sentinel monitors failover
```

2. **Redis Cluster** (Horizontal Scaling)
```
Shard1 (keys hash % 3 == 0)
Shard2 (keys hash % 3 == 1)
Shard3 (keys hash % 3 == 2)
```

## Design Trade-offs

### 1. In-Memory vs Database

**Choice**: In-memory list for metrics

**Rationale:**
- Simplicity for demonstration
- Focus on resilience patterns (not data persistence)
- Fast access for summary computation

**Trade-offs:**
- **Pro**: Simple, fast
- **Con**: Data loss on restart, memory limits
- **Production**: Use PostgreSQL, InfluxDB, or Prometheus

### 2. Fixed Window vs Sliding Window Rate Limiting

**Choice**: Fixed window

**Rationale:**
- Simpler implementation
- Atomic operations in Redis
- "Good enough" for most use cases

**Trade-offs:**
- **Pro**: Simple, efficient, atomic
- **Con**: Burst allowed at window boundaries
- **Example**: Client makes 10 req at 0:59, then 10 req at 1:00 (20 in 1 second)

**Alternative (Sliding Window)**:
```python
# More complex, but smoother limiting
# Use sorted set with timestamps
redis.zadd(key, {timestamp: score})
redis.zremrangebyscore(key, 0, now - window)
count = redis.zcard(key)
```

### 3. Global Services vs Dependency Injection

**Choice**: Hybrid approach

**Rationale:**
- Redis client: Global singleton (infrastructure)
- Service instances: Created per-request (business logic)

**Trade-offs:**
- **Pro**: Efficient resource usage (Redis), testable services
- **Con**: Mixed patterns (could be confusing)

### 4. Synchronous vs Asynchronous

**Choice**: Fully async

**Rationale:**
- FastAPI is async-first
- Redis client is async
- Better concurrency under load

**Trade-offs:**
- **Pro**: Higher throughput, better resource utilization
- **Con**: More complex debugging, async/await everywhere

## Future Enhancements

### Short-term (Next Release)

1. **Authentication & Authorization**
   - API key based authentication
   - Rate limiting per user/tier

2. **Persistent Storage**
   - Migrate from in-memory to PostgreSQL
   - Separate hot/cold data paths

3. **Enhanced Monitoring**
   - Prometheus metrics export
   - Grafana dashboards
   - Distributed tracing (Jaeger)

### Medium-term (3-6 months)

1. **Distributed Architecture**
   - Shared Redis for rate limiting state
   - Distributed circuit breaker
   - Message queue for async processing (Celery/RabbitMQ)

2. **Advanced Analytics**
   - Real-time aggregations
   - Percentile calculations (p50, p95, p99)
   - Time-series specific database (InfluxDB)

3. **API Enhancements**
   - Batch metric ingestion
   - WebSocket for real-time updates
   - GraphQL endpoint

### Long-term (6-12 months)

1. **Multi-region Deployment**
   - Geographic distribution
   - Regional Redis clusters
   - Cross-region replication

2. **Machine Learning Integration**
   - Anomaly detection
   - Predictive scaling
   - Automated threshold tuning

3. **Enterprise Features**
   - Multi-tenancy
   - Custom dashboards
   - SLA monitoring

## Monitoring & Observability

### Logging Strategy

**Current Implementation:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

**Production Recommendations:**

1. **Structured Logging** (JSON)
```python
{
  "timestamp": "2026-02-19T12:00:00Z",
  "level": "INFO",
  "service": "resilient-api",
  "request_id": "abc123",
  "message": "Metric created",
  "metric_type": "cpu_usage",
  "value": 75.5
}
```

2. **Log Aggregation**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- DataDog

3. **Correlation IDs**
- Add request_id to all logs
- Trace requests across services

### Metrics Collection

**Recommended Metrics:**

1. **Application Metrics**
   - Request rate (per endpoint)
   - Response time (p50, p95, p99)
   - Error rate
   - Circuit breaker state changes

2. **Business Metrics**
   - Metrics ingested per second
   - Cache hit rate
   - Rate limit triggers

3. **Infrastructure Metrics**
   - Redis connection pool usage
   - Memory usage
   - CPU usage

### Alerting

**Critical Alerts:**
- Circuit breaker open > 5 minutes
- Redis connection failures
- Error rate > 1%
- Response time p95 > 500ms

**Warning Alerts:**
- Cache hit rate < 70%
- Rate limit triggers > 100/minute
- Memory usage > 80%

## Security Considerations

### Current State

- No authentication (demonstration only)
- Rate limiting provides basic DoS protection
- Input validation via Pydantic

### Production Requirements

1. **Authentication**
   - OAuth2 with JWT tokens
   - API key rotation
   - Rate limiting per user

2. **Transport Security**
   - HTTPS/TLS everywhere
   - Certificate pinning for external services

3. **Data Protection**
   - Encryption at rest (database)
   - Encryption in transit (TLS)
   - PII handling compliance (GDPR, CCPA)

4. **API Security**
   - CORS configuration
   - Input sanitization
   - SQL injection prevention (use parameterized queries)

## Testing Strategy

### Test Pyramid

```
         /\
        /  \  E2E Tests (Few)
       /────\
      /      \ Integration Tests (Some)
     /────────\
    /          \ Unit Tests (Many)
   /────────────\
```

### Current Coverage

1. **Unit Tests** (~60% of test suite)
   - Rate limiter logic
   - Circuit breaker state machine
   - Cache operations

2. **Integration Tests** (~40% of test suite)
   - API endpoint behavior
   - End-to-end flows
   - Redis integration

### Testing Best Practices

1. **Mock External Dependencies**
```python
@pytest.fixture
async def mock_redis():
    return AsyncMock()
```

2. **Test State Transitions**
```python
# Circuit breaker: CLOSED → OPEN → HALF_OPEN → CLOSED
```

3. **Test Edge Cases**
- Empty datasets
- Rate limit boundaries
- Cache expiration timing

## Deployment Architecture

### Docker Compose (Development/Testing)

```yaml
networks:
  resilient-network:
    driver: bridge

services:
  redis:
    image: redis:7-alpine
    healthcheck: {...}
  
  app:
    build: .
    depends_on:
      redis:
        condition: service_healthy
```

### Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resilient-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resilient-api
  template:
    spec:
      containers:
      - name: api
        image: resilient-api:1.0.0
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
```

## Conclusion

This architecture balances simplicity with robustness, demonstrating real-world resilience patterns without over-engineering. The modular design allows for incremental enhancements and scaling as requirements evolve.

Key strengths:
- ✅ Fault tolerant (rate limiting, circuit breaker, caching)
- ✅ High performance (async, caching, connection pooling)
- ✅ Observable (logging, health checks)
- ✅ Testable (dependency injection, mocking)
- ✅ Scalable (stateless design, Redis-backed)

Areas for production enhancement:
- 🔄 Persistent storage (database migration)
- 🔄 Authentication & authorization
- 🔄 Enhanced monitoring (Prometheus, Grafana)
- 🔄 Distributed coordination (for multi-instance)

---

