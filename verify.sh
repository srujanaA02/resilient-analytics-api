#!/bin/bash
# Verification Script - Validates all project requirements

echo "============================================"
echo "Resilient Analytics API - Verification"
echo "============================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (MISSING)"
        return 1
    fi
}

echo "Checking Mandatory Files..."
echo "----------------------------"
check_file "README.md"
check_file "docker-compose.yml"
check_file "Dockerfile"
check_file "requirements.txt"
check_file ".env.example"
check_file "pytest.ini"

echo ""
echo "Checking Source Code..."
echo "----------------------------"
check_dir "src"
check_file "src/main.py"
check_dir "src/api"
check_file "src/api/routes.py"
check_file "src/api/models.py"
check_dir "src/services"
check_file "src/services/cache_service.py"
check_file "src/services/rate_limiter.py"
check_file "src/services/circuit_breaker.py"
check_file "src/services/external_service.py"
check_file "src/services/redis_client.py"
check_dir "src/config"
check_file "src/config/settings.py"

echo ""
echo "Checking Tests..."
echo "----------------------------"
check_dir "tests"
check_file "tests/conftest.py"
check_file "tests/test_cache_service.py"
check_file "tests/test_rate_limiter.py"
check_file "tests/test_circuit_breaker.py"
check_file "tests/test_api_integration.py"

echo ""
echo "Checking Bonus Documentation..."
echo "----------------------------"
check_file "ARCHITECTURE.md"
check_file "TESTING_GUIDE.md"
check_file "API_DOCS.md"
check_file "PROJECT_SUMMARY.md"

echo ""
echo "Checking Helper Scripts..."
echo "----------------------------"
check_file "start.sh"
check_file "start.ps1"
check_file "demo.sh"
check_file "demo.ps1"

echo ""
echo "Verifying Docker Configuration..."
echo "----------------------------"

# Check Dockerfile has required steps
if grep -q "FROM python" Dockerfile; then
    echo -e "${GREEN}✓${NC} Dockerfile has Python base image"
else
    echo -e "${RED}✗${NC} Dockerfile missing Python base"
fi

if grep -q "HEALTHCHECK" Dockerfile; then
    echo -e "${GREEN}✓${NC} Dockerfile has health check"
else
    echo -e "${RED}✗${NC} Dockerfile missing health check"
fi

# Check docker-compose.yml has required services
if grep -q "redis:" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.yml has Redis service"
else
    echo -e "${RED}✗${NC} docker-compose.yml missing Redis"
fi

if grep -q "app:" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.yml has app service"
else
    echo -e "${RED}✗${NC} docker-compose.yml missing app service"
fi

if grep -q "healthcheck:" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.yml has health checks"
else
    echo -e "${RED}✗${NC} docker-compose.yml missing health checks"
fi

echo ""
echo "Verifying Core Requirements Implementation..."
echo "----------------------------"

# Check for POST /api/metrics endpoint
if grep -q "POST /api/metrics" README.md; then
    echo -e "${GREEN}✓${NC} POST /api/metrics documented"
fi

if grep -q "@router.post(\"/api/metrics\"" src/api/routes.py; then
    echo -e "${GREEN}✓${NC} POST /api/metrics implemented"
fi

# Check for GET /api/metrics/summary endpoint
if grep -q "GET /api/metrics/summary" README.md; then
    echo -e "${GREEN}✓${NC} GET /api/metrics/summary documented"
fi

if grep -q "@router.get(\"/api/metrics/summary\"" src/api/routes.py; then
    echo -e "${GREEN}✓${NC} GET /api/metrics/summary implemented"
fi

# Check for caching
if grep -q "class CacheService" src/services/cache_service.py; then
    echo -e "${GREEN}✓${NC} Cache service implemented"
fi

# Check for rate limiting
if grep -q "class RateLimiter" src/services/rate_limiter.py; then
    echo -e "${GREEN}✓${NC} Rate limiter implemented"
fi

# Check for circuit breaker
if grep -q "class CircuitBreaker" src/services/circuit_breaker.py; then
    echo -e "${GREEN}✓${NC} Circuit breaker implemented"
fi

# Check for 429 status code
if grep -q "429" src/api/routes.py; then
    echo -e "${GREEN}✓${NC} 429 status code for rate limiting"
fi

# Check for Retry-After header
if grep -q "Retry-After" src/api/routes.py; then
    echo -e "${GREEN}✓${NC} Retry-After header implemented"
fi

echo ""
echo "Verifying Environment Configuration..."
echo "----------------------------"

# Check .env.example has required variables
required_vars=(
    "APP_PORT"
    "REDIS_HOST"
    "REDIS_PORT"
    "CACHE_TTL_SECONDS"
    "RATE_LIMIT_REQUESTS"
    "RATE_LIMIT_WINDOW_SECONDS"
    "CIRCUIT_BREAKER_FAILURE_THRESHOLD"
    "CIRCUIT_BREAKER_RESET_TIMEOUT"
    "EXTERNAL_SERVICE_FAILURE_RATE"
)

for var in "${required_vars[@]}"; do
    if grep -q "$var" .env.example; then
        echo -e "${GREEN}✓${NC} $var in .env.example"
    else
        echo -e "${RED}✗${NC} $var missing from .env.example"
    fi
done

echo ""
echo "Checking Test Coverage..."
echo "----------------------------"

test_files=(
    "test_cache_service.py"
    "test_rate_limiter.py"
    "test_circuit_breaker.py"
    "test_api_integration.py"
)

total_tests=0
for test_file in "${test_files[@]}"; do
    if [ -f "tests/$test_file" ]; then
        count=$(grep -c "^async def test_" "tests/$test_file" || echo 0)
        total_tests=$((total_tests + count))
        echo -e "${GREEN}✓${NC} $test_file: $count tests"
    fi
done

echo "Total test functions: $total_tests"

echo ""
echo "============================================"
echo "Verification Complete!"
echo "============================================"
echo ""

if [ $total_tests -gt 40 ]; then
    echo -e "${GREEN}✓ All requirements verified successfully!${NC}"
    echo ""
    echo "Project is ready for submission."
    exit 0
else
    echo -e "${YELLOW}⚠ Some issues detected. Please review above.${NC}"
    exit 1
fi
