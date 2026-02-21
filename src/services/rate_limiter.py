import redis.asyncio as redis
import logging
from typing import Tuple
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiting service using Redis fixed-window counter algorithm.
    
    Implements per-IP rate limiting with atomic Redis operations.
    Uses fixed-window approach: counts requests per time window.
    
    Example:
        limiter = RateLimiter(redis_client, threshold=10, window_seconds=60)
        if await limiter.allow_request("192.168.1.1"):
            # Process request
        else:
            # Return 429 Too Many Requests
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        threshold: int = settings.RATE_LIMIT_REQUESTS,
        window_seconds: int = settings.RATE_LIMIT_WINDOW_SECONDS,
    ):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Async Redis client instance
            threshold: Max requests per window (default: 10)
            window_seconds: Time window in seconds (default: 60)
        """
        self.redis = redis_client
        self.threshold = threshold
        self.window_seconds = window_seconds

    async def allow_request(self, client_key: str) -> bool:
        """
        Check if a request should be allowed based on rate limit.
        
        Uses atomic INCR operation to maintain count consistency.
        Sets expiry on first request in window to auto-cleanup keys.
        
        Args:
            client_key: Unique client identifier (typically IP address)
            
        Returns:
            bool: True if request allowed, False if rate limited
            
        Raises:
            redis.ConnectionError: If Redis connection fails
        """
        try:
            current_count = await self.redis.incr(client_key)

            if current_count == 1:
                # Set expiration when first request arrives
                await self.redis.expire(client_key, self.window_seconds)
            elif current_count > self.threshold:
                return False

            return True
        except Exception as e:
            logger.error(f"Error in rate limiter: {e}")
            # Fail open on Redis errors - allow the request
            return True

    async def get_retry_after(self, client_key: str) -> int:
        """Get seconds until the client can make another request."""
        try:
            ttl = await self.redis.ttl(client_key)
            return max(ttl, 1)  # Return at least 1 second
        except Exception as e:
            logger.error(f"Error getting retry_after: {e}")
            return self.window_seconds

    async def reset(self, client_key: str) -> None:
        """Reset the rate limit counter for a client."""
        try:
            await self.redis.delete(client_key)
        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
