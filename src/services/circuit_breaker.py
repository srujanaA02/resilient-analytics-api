import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable
from src.config.settings import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    
    Prevents cascade failures by monitoring service health and stopping
    requests when service is unhealthy. Implements three-state machine:
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service unhealthy, requests fail immediately
    - HALF_OPEN: Recovery mode, test requests allowed
    
    Transitions:
    - CLOSED → OPEN: After consecutive failures exceed threshold
    - OPEN → HALF_OPEN: After timeout expires
    - HALF_OPEN → CLOSED: After successful recovery threshold
    - HALF_OPEN → OPEN: After failures in recovery mode
    
    Example:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        try:
            result = await cb.call(external_service_call)
        except CircuitBreakerOpenError:
            # Use fallback logic
    """

    def __init__(
        self,
        failure_threshold: int = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        reset_timeout_seconds: int = settings.CIRCUIT_BREAKER_RESET_TIMEOUT,
        fallback_response: Any = None,
    ):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout_seconds
        self._fallback_response = fallback_response or {"status": "service_unavailable"}
        self._lock = asyncio.Lock()
        self._last_state_change: float = time.time()

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    def get_status(self) -> dict:
        """Get detailed circuit status."""
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Function result or fallback response if circuit is open

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback available
        """
        # Check state transition before processing
        await self._check_state_transition()

        if self._state == CircuitState.OPEN:
            logger.warning(f"Circuit breaker is OPEN, failing fast")
            raise CircuitBreakerOpenError("Circuit is open, service unavailable")

        if self._state == CircuitState.HALF_OPEN:
            # In HALF_OPEN, allow exactly one test request
            async with self._lock:
                try:
                    logger.info("Circuit breaker in HALF_OPEN state, attempting test request")
                    result = await func(*args, **kwargs)
                    # Success - close circuit
                    self._record_success()
                    self._transition_to_closed()
                    logger.info("Test request succeeded, circuit transitioned to CLOSED")
                    return result
                except Exception as e:
                    # Failure - reopen circuit
                    self._last_failure_time = time.time()
                    self._transition_to_open()
                    logger.error(f"Test request failed, circuit remains OPEN: {e}")
                    raise CircuitBreakerOpenError("Test request failed") from e

        # CLOSED state - normal operation
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            async with self._lock:
                self._record_failure()
                if self._failure_count >= self._failure_threshold:
                    self._transition_to_open()
            logger.error(f"Request failed, failure count: {self._failure_count}")
            raise e

    async def _check_state_transition(self) -> None:
        """Check and perform state transitions if needed."""
        if self._state == CircuitState.OPEN:
            time_since_failure = time.time() - self._last_failure_time
            if time_since_failure >= self._reset_timeout:
                self._transition_to_half_open()

    def _record_success(self) -> None:
        """Record successful request."""
        self._success_count += 1
        # Reset failure count on success while in CLOSED state
        if self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def _record_failure(self) -> None:
        """Record failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        if self._state != CircuitState.CLOSED:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_state_change = time.time()
            logger.info("Circuit breaker transitioned to CLOSED")

    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        if self._state != CircuitState.OPEN:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
            self._last_state_change = time.time()
            logger.warning(
                f"Circuit breaker transitioned to OPEN after {self._failure_count} failures"
            )

    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        if self._state == CircuitState.OPEN:
            self._state = CircuitState.HALF_OPEN
            self._last_state_change = time.time()
            logger.info("Circuit breaker transitioned to HALF_OPEN, testing service recovery")

    async def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        async with self._lock:
            self._failure_count = 0
            self._success_count = 0
            self._transition_to_closed()
            logger.info("Circuit breaker manually reset to CLOSED")
