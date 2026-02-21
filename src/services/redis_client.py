import redis.asyncio as redis
import logging
from typing import Optional
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis connection pooling with singleton pattern.
    
    Manages async Redis connections using connection pooling to ensure
    efficient resource usage and connection reuse. Initializes once and 
    reuses the same connection instance throughout application lifetime.
    
    Features:
    - Singleton pattern: Single instance across application
    - Connection pooling: Reuses connections efficiently
    - Health checks: Automatic connection validation
    - Async operations: Full async/await support
    
    Example:
        # Initialize on app startup
        redis_client = await RedisClient.initialize()
        
        # Use throughout application
        await redis_client.get("key")
        await redis_client.set("key", "value", ex=3600)
        
        # Cleanup on app shutdown
        await RedisClient.close()
    """

    _instance: Optional[redis.Redis] = None

    @classmethod
    async def initialize(cls) -> redis.Redis:
        """
        Initialize Redis connection pool (singleton).
        
        Creates async Redis connection with connection pooling and 
        health checks. Verifies connectivity with PING command.
        Safe to call multiple times; returns existing instance after first call.
        
        Returns:
            redis.Redis: Initialized Redis client instance
            
        Raises:
            redis.ConnectionError: If connection to Redis fails
            redis.ResponseError: If Redis server returns error
            
        Environment variables used:
            - REDIS_HOST: Redis server hostname (default: localhost)
            - REDIS_PORT: Redis server port (default: 6379)
            - REDIS_DB: Redis database number (default: 0)
        """
        if cls._instance is None:
            try:
                cls._instance = await redis.from_url(
                    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                    encoding="utf-8",
                    decode_responses=True,
                    health_check_interval=30,
                )
                await cls._instance.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._instance

    @classmethod
    async def get(cls) -> redis.Redis:
        """Get Redis connection instance."""
        if cls._instance is None:
            await cls.initialize()
        return cls._instance

    @classmethod
    async def close(cls):
        """Close Redis connection."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            logger.info("Redis connection closed")
