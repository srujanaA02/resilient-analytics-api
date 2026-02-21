import asyncio
import random
import logging
from typing import Any, Dict
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Global variable to control failure rate for testing
_simulated_failure_rate = settings.EXTERNAL_SERVICE_FAILURE_RATE


def set_failure_rate(rate: float) -> None:
    """Set the simulated failure rate for testing (0.0 to 1.0)."""
    global _simulated_failure_rate
    if not (0 <= rate <= 1.0):
        raise ValueError("Failure rate must be between 0.0 and 1.0")
    _simulated_failure_rate = rate
    logger.info(f"External service failure rate set to {rate}")


def get_failure_rate() -> float:
    """Get the current simulated failure rate."""
    return _simulated_failure_rate


async def fetch_external_data(metric_type: str = "cpu_usage") -> Dict[str, Any]:
    """
    Simulate an external API call with configurable failure rate.

    Randomly fails based on the configured failure rate.
    Simulates network latency.

    Args:
        metric_type: Type of metric being fetched

    Returns:
        Dictionary with external data

    Raises:
        RuntimeError: Simulated service failure
    """
    # Simulate network latency
    await asyncio.sleep(random.uniform(0.05, 0.15))

    # Randomly fail based on configured failure rate
    if random.random() < _simulated_failure_rate:
        error_msg = f"External service unavailable for {metric_type} due to high load"
        logger.error(f"Simulated external service failure: {error_msg}")
        raise RuntimeError(error_msg)

    # Return mock external data
    external_data = {
        "source": "external_service",
        "metric_type": metric_type,
        "sample_value": random.randint(50, 200),
        "timestamp": asyncio.get_event_loop().time(),
    }

    logger.debug(f"External service returned data for {metric_type}")
    return external_data
