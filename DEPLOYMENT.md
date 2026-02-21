# Deployment Guide

## Local Development

### Prerequisites
- Python 3.11+
- Docker & docker-compose
- Git

### Quick Start
```bash
git clone https://github.com/srujanaA02/resilient-analytics-api
cd resilient-analytics-api
docker-compose up
```

API available at `http://localhost:8000`

## Environment Variables

Create `.env` based on `.env.example`:

```env
# API Configuration
APP_NAME=Resilient Analytics API
DEBUG=false
LOG_LEVEL=INFO

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Circuit Breaker
CB_FAILURE_THRESHOLD=5
CB_RECOVERY_TIMEOUT=60
CB_SUCCESS_THRESHOLD=2

# Cache
CACHE_TTL=300

# External Service
EXTERNAL_SERVICE_FAILURE_RATE=0.1
```

## Docker Deployment

### Build Image
```bash
docker build -t resilient-api:latest .
```

### Run Container
```bash
docker run -d \
  --name resilient-api \
  -p 8000:8000 \
  --env-file .env \
  resilient-api:latest
```

### Health Check
```bash
curl http://localhost:8000/api/health
```

## Production Considerations

### Scalability
- Use Redis Cluster for high throughput
- Deploy multiple app instances behind load balancer
- Configure connection pooling appropriately

### Monitoring
- Monitor Redis memory usage
- Track rate limit violations
- Monitor circuit breaker state transitions
- Log all external service failures

### Security
- Enable Redis authentication
- Use environment secrets management
- Implement API authentication (JWT recommended)
- Use HTTPS/TLS in production

### Backup & Recovery
- Configure Redis persistence (AOF or RDB)
- Implement regular backup strategy
- Test recovery procedures

## Troubleshooting

### Connection Refused
- Verify Redis is running: `docker-compose ps`
- Check Redis port: `redis-cli -h redis ping`

### Rate Limit Issues
- Verify rate limit window: Check logs
- Reset limits: `redis-cli FLUSHDB`

### Circuit Breaker Open
- Monitor external service health
- Check circuit breaker status endpoint: `/api/circuit-breaker/status`
- Manual reset: Restart service
