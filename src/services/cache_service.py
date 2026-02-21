import redis.asyncio as redis
import json
import logging
from typing import Any, Callable, Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-backed caching service with TTL support."""

    def __init__(
        self, redis_client: redis.Redis, default_ttl_seconds: int = settings.CACHE_TTL_SECONDS
    ):
        self.redis = redis_client
        self.default_ttl_seconds = default_ttl_seconds

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            cached_data = await self.redis.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        try:
            ttl = ttl_seconds or self.default_ttl_seconds
            await self.redis.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cache set for key '{key}' with TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {e}")
            return False

    async def get_or_set(
        self,
        key: str,
        data_fetch_func: Callable,
        ttl_seconds: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or fetch and cache it.

        Args:
            key: Cache key
            data_fetch_func: Async function to fetch data if not in cache
            ttl_seconds: TTL for the cached data

        Returns:
            Cached or fetched data
        """
        # Try to get from cache
        cached_data = await self.get(key)
        if cached_data is not None:
            logger.debug(f"Cache hit for key '{key}'")
            return cached_data

        # Cache miss, fetch data
        logger.debug(f"Cache miss for key '{key}', fetching data")
        data = await data_fetch_func()

        # Store in cache
        await self.set(key, data, ttl_seconds)

        return data

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern '{pattern}': {e}")
            return 0
