from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging

from src.api.models import (
    MetricRequest,
    MetricResponse,
    MetricSummary,
    ErrorResponse,
    HealthCheckResponse,
    CircuitBreakerStatus,
)
from src.services.redis_client import RedisClient
from src.services.rate_limiter import RateLimiter
from src.services.cache_service import CacheService
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.services.external_service import fetch_external_data
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory metric storage (in production, use a database)
metrics_db: List[MetricRequest] = []

# Global services (initialized on startup)
rate_limiter: Optional[RateLimiter] = None
cache_service: Optional[CacheService] = None
circuit_breaker: Optional[CircuitBreaker] = None


async def get_services():
    """Get service instances."""
    global rate_limiter, cache_service, circuit_breaker

    if rate_limiter is None:
        redis = await RedisClient.get()
        rate_limiter = RateLimiter(redis)
        cache_service = CacheService(redis)
        circuit_breaker = CircuitBreaker()

    return rate_limiter, cache_service, circuit_breaker


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        redis = await RedisClient.get()
        await redis.ping()
        redis_connected = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_connected = False

    return HealthCheckResponse(
        status="healthy" if redis_connected else "degraded",
        redis_connected=redis_connected,
    )


@router.post("/api/metrics", status_code=201, response_model=dict)
async def create_metric(metric: MetricRequest, request: Request):
    """
    Ingest a new metric.

    Rate limiting is applied per client IP address.
    """
    rate_limiter, _, _ = await get_services()

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:{client_ip}"

    # Check rate limit
    allowed = await rate_limiter.allow_request(rate_limit_key)
    if not allowed:
        retry_after = await rate_limiter.get_retry_after(rate_limit_key)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    # Store metric with normalized timezone-aware timestamp
    try:
        # Ensure timestamp is timezone-aware (convert to UTC if needed)
        if metric.timestamp.tzinfo is None:
            metric.timestamp = metric.timestamp.replace(tzinfo=timezone.utc)
        else:
            metric.timestamp = metric.timestamp.astimezone(timezone.utc)
        
        metrics_db.append(metric)
        logger.info(f"Metric stored: type={metric.type}, value={metric.value}")
        return {
            "message": "Metric received",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": metric.type,
        }
    except Exception as e:
        logger.error(f"Error storing metric: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/metrics/summary", response_model=MetricSummary)
async def get_metrics_summary(type: str, period: str = "all"):
    """
    Get aggregated metrics summary.

    Results are cached using Redis with configurable TTL.
    The circuit breaker pattern protects calls to external services.

    Query parameters:
    - type: Metric type to summarize (required)
    - period: Time period (all, daily, hourly) - default: all
    """
    _, cache_service, circuit_breaker = await get_services()

    # Validate period
    valid_periods = ["all", "daily", "hourly"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    # Check cache
    cache_key = f"summary:{type}:{period}"

    try:
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for {cache_key}")
            return MetricSummary(**cached_data)
    except Exception as e:
        logger.error(f"Cache retrieval error: {e}")

    # Compute summary
    try:
        summary = compute_summary(type, period)

        # Attempt to call external service with circuit breaker
        try:
            external_data = await circuit_breaker.call(fetch_external_data, type)
            logger.debug(f"External service data: {external_data}")
        except CircuitBreakerOpenError:
            logger.warning("Circuit breaker open, using local data only")
        except Exception as e:
            logger.error(f"External service call failed: {e}")

        # Cache the result
        try:
            await cache_service.set(cache_key, summary.dict())
        except Exception as e:
            logger.error(f"Cache set error: {e}")

        return summary

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def compute_summary(metric_type: str, period: str) -> MetricSummary:
    """
    Compute metrics summary from in-memory store.

    Args:
        metric_type: Type of metrics to summarize
        period: Time period filter (all, daily, hourly)

    Returns:
        Aggregated metrics summary
    """
    # Filter metrics by type
    filtered_metrics = [m for m in metrics_db if m.type == metric_type]

    if not filtered_metrics:
        # Return empty summary
        return MetricSummary(
            type=metric_type,
            period=period,
            count=0,
            average_value=0.0,
            min_value=0.0,
            max_value=0.0,
            latest_value=0.0,
        )

    # Filter by time period
    now = datetime.now(timezone.utc)
    if period == "daily":
        cutoff = now - timedelta(days=1)
        filtered_metrics = [m for m in filtered_metrics if m.timestamp >= cutoff]
    elif period == "hourly":
        cutoff = now - timedelta(hours=1)
        filtered_metrics = [m for m in filtered_metrics if m.timestamp >= cutoff]

    if not filtered_metrics:
        return MetricSummary(
            type=metric_type,
            period=period,
            count=0,
            average_value=0.0,
            min_value=0.0,
            max_value=0.0,
            latest_value=0.0,
        )

    values = [m.value for m in filtered_metrics]

    return MetricSummary(
        type=metric_type,
        period=period,
        count=len(values),
        average_value=sum(values) / len(values),
        min_value=min(values),
        max_value=max(values),
        latest_value=values[-1],
    )


@router.get("/api/metrics/list", response_model=List[MetricResponse])
async def get_metrics(type: Optional[str] = None, limit: int = 100):
    """Get list of metrics with optional type filter."""
    result = metrics_db[-limit:] if not type else [m for m in metrics_db if m.type == type][-limit:]

    return [
        MetricResponse(
            timestamp=m.timestamp,
            value=m.value,
            type=m.type,
        )
        for m in result
    ]


@router.get("/api/circuit-breaker/status", response_model=CircuitBreakerStatus)
async def get_circuit_breaker_status():
    """Get circuit breaker status."""
    _, _, circuit_breaker = await get_services()
    status = circuit_breaker.get_status()

    return CircuitBreakerStatus(
        state=status["state"],
        failure_count=status["failure_count"],
        success_count=status["success_count"],
    )


@router.get("/api/external")
async def call_external_service():
    """
    Call external service with circuit breaker protection.
    
    This endpoint demonstrates the circuit breaker pattern by calling
    a simulated external service that may fail based on configured failure rate.
    """
    _, _, circuit_breaker = await get_services()
    
    try:
        result = await circuit_breaker.call(fetch_external_data, metric_type="external_request")
        return {
            "status": "success",
            "source": "external_service",
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except CircuitBreakerOpenError as e:
        logger.warning("Circuit breaker open, returning fallback")
        return {
            "status": "fallback",
            "source": "circuit_breaker_fallback",
            "message": "External service unavailable, using fallback",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(
            status_code=503,
            detail="External service temporarily unavailable"
        )
