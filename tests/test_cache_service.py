import pytest
import json
from unittest.mock import AsyncMock
from src.services.cache_service import CacheService


@pytest.fixture
async def mock_redis():
    """Create a mock Redis client."""
    redis_mock = AsyncMock()
    return redis_mock


@pytest.fixture
async def cache_service(mock_redis):
    """Create a cache service instance with mock Redis."""
    return CacheService(redis_client=mock_redis, default_ttl_seconds=300)


@pytest.mark.asyncio
async def test_cache_get_hit(cache_service, mock_redis):
    """Test cache hit."""
    test_data = {"key": "value", "number": 42}
    mock_redis.get.return_value = json.dumps(test_data)

    result = await cache_service.get("test_key")

    assert result == test_data
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_get_miss(cache_service, mock_redis):
    """Test cache miss."""
    mock_redis.get.return_value = None

    result = await cache_service.get("test_key")

    assert result is None
    mock_redis.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_set(cache_service, mock_redis):
    """Test cache set operation."""
    test_data = {"key": "value"}
    mock_redis.setex.return_value = True

    result = await cache_service.set("test_key", test_data)

    assert result is True
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "test_key"
    assert call_args[0][1] == 300
    assert call_args[0][2] == json.dumps(test_data)


@pytest.mark.asyncio
async def test_cache_set_custom_ttl(cache_service, mock_redis):
    """Test cache set with custom TTL."""
    test_data = {"key": "value"}
    mock_redis.setex.return_value = True

    await cache_service.set("test_key", test_data, ttl_seconds=600)

    call_args = mock_redis.setex.call_args
    assert call_args[0][1] == 600


@pytest.mark.asyncio
async def test_cache_delete(cache_service, mock_redis):
    """Test cache delete operation."""
    mock_redis.delete.return_value = 1

    result = await cache_service.delete("test_key")

    assert result is True
    mock_redis.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_cache_get_or_set_hit(cache_service, mock_redis):
    """Test get_or_set with cache hit."""
    test_data = {"key": "value"}
    mock_redis.get.return_value = json.dumps(test_data)

    fetch_func = AsyncMock()

    result = await cache_service.get_or_set("test_key", fetch_func)

    assert result == test_data
    fetch_func.assert_not_called()


@pytest.mark.asyncio
async def test_cache_get_or_set_miss(cache_service, mock_redis):
    """Test get_or_set with cache miss and subsequent set."""
    test_data = {"key": "value", "fetched": True}
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True

    async def fetch_func():
        return test_data

    result = await cache_service.get_or_set("test_key", fetch_func)

    assert result == test_data
    mock_redis.get.assert_called_once_with("test_key")
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_clear_pattern(cache_service, mock_redis):
    """Test clearing cache by pattern."""
    mock_redis.keys.return_value = ["key1", "key2", "key3"]
    mock_redis.delete.return_value = 3

    result = await cache_service.clear_pattern("summary:*")

    assert result == 3
    mock_redis.keys.assert_called_once_with("summary:*")
    mock_redis.delete.assert_called_once_with("key1", "key2", "key3")


@pytest.mark.asyncio
async def test_cache_clear_pattern_no_keys(cache_service, mock_redis):
    """Test clearing cache by pattern when no keys match."""
    mock_redis.keys.return_value = []

    result = await cache_service.clear_pattern("nonexistent:*")

    assert result == 0
    mock_redis.keys.assert_called_once_with("nonexistent:*")


@pytest.mark.asyncio
async def test_cache_redis_error_handling(cache_service, mock_redis):
    """Test cache service error handling."""
    mock_redis.get.side_effect = Exception("Redis connection lost")

    result = await cache_service.get("test_key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_set_redis_error_handling(cache_service, mock_redis):
    """Test cache set error handling."""
    mock_redis.setex.side_effect = Exception("Redis connection lost")

    result = await cache_service.set("test_key", {"data": "value"})

    assert result is False
