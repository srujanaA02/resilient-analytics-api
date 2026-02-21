import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.rate_limiter import RateLimiter
from src.config.settings import settings


@pytest.fixture
async def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    return redis_mock


@pytest.fixture
async def rate_limiter(mock_redis):
    """Create a rate limiter instance with mock Redis."""
    return RateLimiter(
        redis_client=mock_redis,
        threshold=3,
        window_seconds=60,
    )


@pytest.mark.asyncio
async def test_allow_first_request(rate_limiter, mock_redis):
    """Test that first request is allowed."""
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True

    result = await rate_limiter.allow_request("client_1")

    assert result is True
    mock_redis.incr.assert_called_once_with("client_1")
    mock_redis.expire.assert_called_once_with("client_1", 60)


@pytest.mark.asyncio
async def test_allow_requests_within_limit(rate_limiter, mock_redis):
    """Test that requests within limit are allowed."""
    # Simulate 3 requests
    mock_redis.incr.side_effect = [1, 2, 3]
    mock_redis.expire.return_value = True

    for i in range(1, 4):
        result = await rate_limiter.allow_request("client_1")
        assert result is True


@pytest.mark.asyncio
async def test_rate_limit_exceeded(rate_limiter, mock_redis):
    """Test that requests exceeding limit are rejected."""
    # Simulate request count exceeding threshold
    mock_redis.incr.return_value = 4

    result = await rate_limiter.allow_request("client_1")

    assert result is False


@pytest.mark.asyncio
async def test_get_retry_after(rate_limiter, mock_redis):
    """Test getting retry-after value."""
    mock_redis.ttl.return_value = 30

    retry_after = await rate_limiter.get_retry_after("client_1")

    assert retry_after == 30
    mock_redis.ttl.assert_called_once_with("client_1")


@pytest.mark.asyncio
async def test_get_retry_after_min_value(rate_limiter, mock_redis):
    """Test that retry-after returns at least 1 second."""
    mock_redis.ttl.return_value = -1

    retry_after = await rate_limiter.get_retry_after("client_1")

    assert retry_after == 1


@pytest.mark.asyncio
async def test_rate_limiter_redis_error_handling(rate_limiter, mock_redis):
    """Test that rate limiter fails open on Redis errors."""
    mock_redis.incr.side_effect = Exception("Redis connection lost")

    result = await rate_limiter.allow_request("client_1")

    # Should allow request (fail open)
    assert result is True


@pytest.mark.asyncio
async def test_reset_rate_limit(rate_limiter, mock_redis):
    """Test resetting rate limit counter."""
    mock_redis.delete.return_value = 1

    await rate_limiter.reset("client_1")

    mock_redis.delete.assert_called_once_with("client_1")
