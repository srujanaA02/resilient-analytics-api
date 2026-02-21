import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def clear_redis():
    """Clear Redis before each test to prevent state interference."""
    try:
        from src.services.redis_client import RedisClient
        redis = await RedisClient.get()
        await redis.flushall()
    except Exception:
        pass  # Skip if Redis not available
    yield
    try:
        redis = await RedisClient.get()
        await redis.flushall()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def override_rate_limit(monkeypatch):
    """Override rate limit for tests to prevent test failures."""
    # Must patch before settings module is imported
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "100")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    # Force reload settings
    from src.config import settings as settings_module
    settings_module.settings.RATE_LIMIT_REQUESTS = 100
    settings_module.settings.RATE_LIMIT_WINDOW_SECONDS = 60


@pytest.fixture
def mock_redis_global():
    """Mock Redis client for entire session."""
    with patch('src.services.redis_client.RedisClient._instance', None):
        yield


@pytest.fixture(autouse=True)
def metrics_db_clean():
    """Clear metrics database before and after each test."""
    from src.api import routes
    routes.metrics_db.clear()
    # Reset rate limiter and cache instances
    routes.rate_limiter = None
    routes.cache_service = None
    routes.circuit_breaker = None
    yield
    routes.metrics_db.clear()
    routes.rate_limiter = None
    routes.cache_service = None
    routes.circuit_breaker = None
