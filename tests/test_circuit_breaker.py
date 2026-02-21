import pytest
import asyncio
import time
from src.services.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker instance."""
    return CircuitBreaker(failure_threshold=3, reset_timeout_seconds=1)


@pytest.mark.asyncio
async def test_circuit_breaker_initial_state(circuit_breaker):
    """Test circuit breaker starts in CLOSED state."""
    assert circuit_breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success(circuit_breaker):
    """Test circuit breaker allows successful requests in CLOSED state."""

    async def successful_func():
        return "success"

    result = await circuit_breaker.call(successful_func)
    assert result == "success"
    assert circuit_breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(circuit_breaker):
    """Test circuit breaker opens after threshold failures."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Trigger failures until threshold is reached
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open(circuit_breaker):
    """Test circuit breaker rejects requests immediately when OPEN."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Open the circuit
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    # Try to make a request when open
    async def another_request():
        return "should fail"

    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(another_request)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout(circuit_breaker):
    """Test circuit breaker transitions to HALF_OPEN after reset timeout."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Open the circuit
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.get_state() == CircuitState.OPEN

    # Wait for reset timeout
    await asyncio.sleep(1.1)

    # Try to make a request - should attempt in HALF_OPEN and fail
    # Expecting CircuitBreakerOpenError since test request fails
    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_func)

    # Circuit should be OPEN again after failed half-open test
    assert circuit_breaker.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successful_test(circuit_breaker):
    """Test circuit breaker closes after successful test request in HALF_OPEN state."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Open the circuit
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.get_state() == CircuitState.OPEN

    # Wait for reset timeout
    await asyncio.sleep(1.1)

    # Manually set state to HALF_OPEN for testing
    circuit_breaker._state = CircuitState.HALF_OPEN

    # Make a successful request
    async def successful_func():
        return "success"

    result = await circuit_breaker.call(successful_func)
    assert result == "success"
    assert circuit_breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_reopens_after_half_open_failure(circuit_breaker):
    """Test circuit breaker reopens if test request fails in HALF_OPEN state."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Open the circuit
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    # Set to HALF_OPEN
    circuit_breaker._state = CircuitState.HALF_OPEN

    # Make a failing request
    with pytest.raises(CircuitBreakerOpenError):
        await circuit_breaker.call(failing_func)

    assert circuit_breaker.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_manual_reset(circuit_breaker):
    """Test manual reset of circuit breaker."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Open the circuit
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    assert circuit_breaker.get_state() == CircuitState.OPEN

    # Manual reset
    await circuit_breaker.reset()
    assert circuit_breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_status(circuit_breaker):
    """Test getting circuit breaker status."""
    status = circuit_breaker.get_status()

    assert status["state"] == "CLOSED"
    assert status["failure_count"] == 0
    assert status["success_count"] == 0


@pytest.mark.asyncio
async def test_circuit_breaker_failure_count_increments(circuit_breaker):
    """Test that failure count increments correctly."""

    async def failing_func():
        raise RuntimeError("Service error")

    # Make 2 failing requests
    for i in range(2):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

    status = circuit_breaker.get_status()
    assert status["failure_count"] == 2

    # Success should reset failure count
    async def successful_func():
        return "success"

    await circuit_breaker.call(successful_func)
    status = circuit_breaker.get_status()
    assert status["failure_count"] == 0
    assert status["success_count"] == 1
