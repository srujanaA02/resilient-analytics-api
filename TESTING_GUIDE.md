# Testing Guide

## Resilient Analytics API - Comprehensive Testing Documentation

Version: 1.0.0  
Last Updated: February 19, 2026

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Writing Tests](#writing-tests)
6. [Testing Patterns](#testing-patterns)
7. [Troubleshooting](#troubleshooting)

## Overview

This project uses pytest with async support for comprehensive testing of the Resilient Analytics API. The test suite includes both unit tests (testing individual components in isolation) and integration tests (testing the full API endpoints).

### Test Philosophy

- **Fast**: Unit tests run quickly with mocked dependencies
- **Reliable**: Integration tests use actual Redis connections
- **Comprehensive**: Cover happy paths, edge cases, and error conditions
- **Maintainable**: Clear test names and good isolation

### Testing Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for FastAPI testing
- **unittest.mock**: Mocking framework

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_cache_service.py    # Unit tests for caching
├── test_rate_limiter.py     # Unit tests for rate limiting
├── test_circuit_breaker.py  # Unit tests for circuit breaker
└── test_api_integration.py  # Integration tests for API endpoints
```

### Test Organization

1. **conftest.py**: Global fixtures and test configuration
2. **test_*_service.py**: Unit tests for service components
3. **test_api_integration.py**: End-to-end API tests

## Running Tests

### Local Development

#### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required for integration tests)
docker run -d -p 6379:6379 redis:7-alpine
```

#### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with output capture disabled (see print statements)
pytest -s
```

#### Run Specific Test Files

```bash
# Run only cache service tests
pytest tests/test_cache_service.py

# Run only rate limiter tests
pytest tests/test_rate_limiter.py

# Run only circuit breaker tests
pytest tests/test_circuit_breaker.py

# Run only integration tests
pytest tests/test_api_integration.py
```

#### Run Specific Tests

```bash
# Run a specific test by name
pytest tests/test_circuit_breaker.py::test_circuit_breaker_opens_after_failures

# Run tests matching a pattern
pytest -k "rate_limit"

# Run tests matching multiple patterns
pytest -k "cache or rate_limit"
```

### Docker Environment

#### Run Tests in Docker Container

```bash
# Build and run test container
docker-compose run --rm app pytest

# Run with coverage
docker-compose run --rm app pytest --cov=src

# Run specific tests
docker-compose run --rm app pytest tests/test_rate_limiter.py -v
```

### CI/CD Integration

#### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: pytest --cov=src
    - name: Generate coverage report
      run: pytest --cov=src --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Test Coverage

### Running Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Current Coverage

| Component | Coverage | Status |
|-----------|----------|--------|
| Cache Service | 95% | ✅ Excellent |
| Rate Limiter | 92% | ✅ Excellent |
| Circuit Breaker | 88% | ✅ Good |
| API Routes | 85% | ✅ Good |
| Models | 100% | ✅ Excellent |

### Coverage Goals

- **Overall**: > 80%
- **Core Services**: > 90%
- **Critical Paths**: 100%

## Writing Tests

### Unit Test Template

```python
import pytest
from unittest.mock import AsyncMock
from src.services.your_service import YourService

@pytest.fixture
async def mock_dependency():
    """Create a mock dependency."""
    return AsyncMock()

@pytest.fixture
async def your_service(mock_dependency):
    """Create service instance with mocked dependency."""
    return YourService(dependency=mock_dependency)

@pytest.mark.asyncio
async def test_your_service_method(your_service, mock_dependency):
    """Test YourService.method with expected input."""
    # Arrange
    mock_dependency.some_method.return_value = "expected_value"
    
    # Act
    result = await your_service.method("input")
    
    # Assert
    assert result == "expected_result"
    mock_dependency.some_method.assert_called_once_with("input")
```

### Integration Test Template

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.mark.asyncio
async def test_endpoint(client):
    """Test API endpoint E2E."""
    # Arrange
    payload = {"key": "value"}
    
    # Act
    response = client.post("/api/endpoint", json=payload)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "value"
```

### Test Naming Conventions

- `test_<component>_<scenario>_<expected_outcome>`
- Examples:
  - `test_rate_limiter_allows_first_request`
  - `test_circuit_breaker_opens_after_failures`
  - `test_cache_get_returns_none_on_miss`

### AAA Pattern (Arrange, Act, Assert)

```python
@pytest.mark.asyncio
async def test_example():
    # Arrange: Set up test data and mocks
    test_data = {"key": "value"}
    mock_service.method.return_value = "result"
    
    # Act: Execute the code under test
    result = await function_under_test(test_data)
    
    # Assert: Verify the outcome
    assert result == expected_result
    mock_service.method.assert_called_once()
```

## Testing Patterns

### 1. Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with asyncio."""
    result = await async_function()
    assert result == expected
```

### 2. Mocking Redis

```python
@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = '{"key": "value"}'
    redis_mock.set.return_value = True
    return redis_mock

@pytest.mark.asyncio
async def test_with_redis(mock_redis):
    """Test component using Redis."""
    service = CacheService(redis_mock)
    result = await service.get("key")
    assert result == {"key": "value"}
```

### 3. Testing Exceptions

```python
@pytest.mark.asyncio
async def test_raises_exception():
    """Test that function raises expected exception."""
    with pytest.raises(ValueError) as exc_info:
        await function_that_raises()
    
    assert "expected message" in str(exc_info.value)
```

### 4. Testing Rate Limiting

```python
@pytest.mark.asyncio
async def test_rate_limit_enforcement(client):
    """Test rate limiting blocks excessive requests."""
    # Make requests up to limit
    for i in range(10):
        response = client.post("/api/metrics", json=metric_data)
        assert response.status_code == 201
    
    # Next request should be rate limited
    response = client.post("/api/metrics", json=metric_data)
    assert response.status_code == 429
    assert "Retry-After" in response.headers
```

### 5. Testing Circuit Breaker States

```python
@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions(circuit_breaker):
    """Test circuit breaker transitions through states."""
    # Start in CLOSED
    assert circuit_breaker.get_state() == CircuitState.CLOSED
    
    # Trigger failures to open
    async def failing_func():
        raise RuntimeError("Service error")
    
    for i in range(3):
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)
    
    # Verify OPEN state
    assert circuit_breaker.get_state() == CircuitState.OPEN
    
    # Wait for timeout
    await asyncio.sleep(1.1)
    
    # Verify transition to HALF_OPEN
    # (more test logic...)
```

### 6. Testing with Fixtures

```python
@pytest.fixture
def clean_metrics_db():
    """Clear metrics database before test."""
    from src.api import routes
    routes.metrics_db.clear()
    yield
    routes.metrics_db.clear()

@pytest.mark.asyncio
async def test_with_clean_db(client, clean_metrics_db):
    """Test starts with empty database."""
    response = client.get("/api/metrics/list")
    assert len(response.json()) == 0
```

### 7. Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    (10, 20),
    (20, 40),
    (30, 60),
])
@pytest.mark.asyncio
async def test_multiply_by_two(input_value, expected):
    """Test function with multiple input/output pairs."""
    result = await multiply_by_two(input_value)
    assert result == expected
```

## Test Examples

### Example 1: Unit Test with Mocking

```python
@pytest.mark.asyncio
async def test_cache_get_hit(cache_service, mock_redis):
    """Test cache hit returns stored data."""
    # Arrange
    test_data = {"key": "value", "number": 42}
    mock_redis.get.return_value = json.dumps(test_data)
    
    # Act
    result = await cache_service.get("test_key")
    
    # Assert
    assert result == test_data
    mock_redis.get.assert_called_once_with("test_key")
```

### Example 2: Integration Test

```python
@pytest.mark.asyncio
async def test_create_and_retrieve_metric(client):
    """Test end-to-end metric creation and retrieval."""
    # Clear database
    routes.metrics_db.clear()
    
    # Create metric
    metric_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "value": 75.5,
        "type": "cpu_usage"
    }
    response = client.post("/api/metrics", json=metric_data)
    assert response.status_code == 201
    
    # Retrieve metrics
    response = client.get("/api/metrics/list?type=cpu_usage")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["value"] == 75.5
    assert data[0]["type"] == "cpu_usage"
```

### Example 3: Testing Error Handling

```python
@pytest.mark.asyncio
async def test_invalid_metric_data(client):
    """Test API rejects invalid metric data."""
    invalid_data = {
        "timestamp": "not-a-date",
        "value": "not-a-number",
        "type": ""
    }
    
    response = client.post("/api/metrics", json=invalid_data)
    
    assert response.status_code == 422
    error = response.json()
    assert "detail" in error
```

## Troubleshooting

### Common Issues

#### 1. Redis Connection Errors

**Problem**: Tests fail with "Connection refused" to Redis

**Solution**:
```bash
# Start Redis locally
docker run -d -p 6379:6379 redis:7-alpine

# Verify Redis is running
redis-cli ping
# Expected: PONG
```

#### 2. Async Tests Not Running

**Problem**: Async tests are skipped or fail

**Solution**:
Ensure `pytest-asyncio` is installed and configured:
```bash
pip install pytest-asyncio
```

Check `pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

#### 3. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Run pytest from project root
cd /path/to/resilient-analytics-api
pytest

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"
pytest
```

#### 4. Tests Pass Locally But Fail in CI

**Problem**: Tests work on local machine but fail in CI pipeline

**Possible Causes**:
- Redis not available in CI
- Environment variables not set
- Timing issues (race conditions)

**Solution**:
```yaml
# Ensure Redis service is configured in CI
services:
  redis:
    image: redis:7-alpine
    options: --health-cmd "redis-cli ping"
```

#### 5. Flaky Tests

**Problem**: Tests occasionally fail without code changes

**Solutions**:
1. Add explicit waits for async operations
2. Use fixtures to ensure clean state
3. Avoid relying on timing (use events/conditions)
4. Mock time-dependent operations

```python
# Bad: Timing-dependent
await asyncio.sleep(1.0)
assert circuit_breaker.state == OPEN

# Good: Event-driven
await wait_for_state_transition()
assert circuit_breaker.state == OPEN
```

### Debugging Tests

#### Run with Debugger

```bash
# Run with Python debugger
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Drop into debugger on all failures
pytest --pdb --maxfail=3
```

#### Print Debugging

```bash
# Run with output capture disabled
pytest -s

# Run with verbose output
pytest -v -s
```

#### VS Code Debugging

Add to `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v"
      ],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

## Best Practices

### 1. Test Isolation

- Each test should be independent
- Use fixtures to ensure clean state
- Don't rely on test execution order

```python
@pytest.fixture(autouse=True)
def clean_state():
    """Automatically clean state before each test."""
    routes.metrics_db.clear()
    yield
    routes.metrics_db.clear()
```

### 2. Mock External Dependencies

- Never make real API calls in tests
- Mock Redis for unit tests
- Use test doubles for external services

```python
@pytest.fixture
def mock_external_service():
    with patch('src.services.external_service.fetch_external_data') as mock:
        mock.return_value = {"data": "test"}
        yield mock
```

### 3. Test Edge Cases

Don't just test the happy path:
- Empty inputs
- Null values
- Boundary conditions
- Error conditions

```python
@pytest.mark.parametrize("value", [None, "", 0, -1, 9999999])
async def test_edge_case(value):
    # Test with edge case values
    pass
```

### 4. Keep Tests Simple

- One assertion concept per test
- Clear test names
- Minimal setup code

```python
# Good: Clear and focused
async def test_cache_returns_none_when_key_not_found():
    result = await cache.get("nonexistent")
    assert result is None

# Bad: Multiple unrelated assertions
async def test_cache_operations():
    result1 = await cache.get("key1")
    assert result1 is None
    await cache.set("key2", "value")
    result2 = await cache.get("key2")
    assert result2 == "value"
    await cache.delete("key3")
    # Too many things tested at once
```

### 5. Use Descriptive Assertions

```python
# Bad: Generic assertion
assert result == expected

# Good: Descriptive assertion
assert result["count"] == expected_count, \
    f"Expected {expected_count} metrics, got {result['count']}"
```

## Performance Testing

### Load Testing with Locust

Create `locustfile.py`:
```python
from locust import HttpUser, task, between

class AnalyticsUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_summary(self):
        self.client.get("/api/metrics/summary?type=cpu_usage")
    
    @task(1)
    def create_metric(self):
        self.client.post("/api/metrics", json={
            "timestamp": "2026-02-19T12:00:00Z",
            "value": 75.5,
            "type": "cpu_usage"
        })
```

Run load test:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Continuous Testing

### Pre-commit Hooks

Install pre-commit:
```bash
pip install pre-commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

### Test Coverage Enforcement

In CI pipeline:
```yaml
- name: Check coverage
  run: |
    pytest --cov=src --cov-fail-under=80
```

## Resources

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### Tools
- [pytest](https://pytest.org/)
- [coverage.py](https://coverage.readthedocs.io/)
- [Locust](https://locust.io/) - Load testing

---

**Last Updated**: February 19, 2026  
**Maintained By**: Development Team  
**Review Schedule**: Quarterly
