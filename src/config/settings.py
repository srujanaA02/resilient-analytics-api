import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Application settings
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # Cache settings
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Circuit breaker settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(
        os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")
    )
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = int(
        os.getenv("CIRCUIT_BREAKER_RESET_TIMEOUT", "30")
    )

    # External service settings
    EXTERNAL_SERVICE_FAILURE_RATE: float = float(
        os.getenv("EXTERNAL_SERVICE_FAILURE_RATE", "0.1")
    )
    EXTERNAL_SERVICE_TIMEOUT: int = int(
        os.getenv("EXTERNAL_SERVICE_TIMEOUT", "5")
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate critical settings on startup."""
        try:
            assert 0 <= cls.EXTERNAL_SERVICE_FAILURE_RATE <= 1.0
            assert cls.RATE_LIMIT_REQUESTS > 0
            assert cls.CACHE_TTL_SECONDS > 0
            assert cls.CIRCUIT_BREAKER_FAILURE_THRESHOLD > 0
            assert cls.CIRCUIT_BREAKER_RESET_TIMEOUT > 0
            return True
        except AssertionError as e:
            raise ValueError(f"Invalid configuration: {e}")


settings = Settings()
