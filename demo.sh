#!/bin/bash
# Demo Script for Resilient Analytics API
# This script demonstrates all API endpoints with example requests

BASE_URL="http://localhost:8000"

echo "============================================"
echo "Resilient Analytics API - Demo Script"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# 1. Health Check
print_section "1. Health Check"
print_info "GET $BASE_URL/health"
curl -s "$BASE_URL/health" | jq .
print_success "Health check completed"

# 2. Create Metrics
print_section "2. Creating Sample Metrics"

metric_types=("cpu_usage" "memory_usage" "disk_usage")
base_values=(60 70 80)

for i in {1..5}; do
    for j in {0..2}; do
        metric_type=${metric_types[$j]}
        base_value=${base_values[$j]}
        value=$((base_value + RANDOM % 20))
        
        timestamp=$(date -u -d "-$i hours" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-${i}H +"%Y-%m-%dT%H:%M:%SZ")
        
        print_info "Creating $metric_type metric (value: $value)"
        
        response=$(curl -s -X POST "$BASE_URL/api/metrics" \
            -H "Content-Type: application/json" \
            -d "{
                \"timestamp\": \"$timestamp\",
                \"value\": $value,
                \"type\": \"$metric_type\"
            }")
        
        if echo "$response" | grep -q "Metric received"; then
            echo "  ✓ Created"
        else
            echo "  ✗ Failed: $response"
        fi
    done
done

print_success "Sample metrics created"

# 3. Get Metrics Summary
print_section "3. Getting Metrics Summary"

print_info "GET $BASE_URL/api/metrics/summary?type=cpu_usage&period=all"
curl -s "$BASE_URL/api/metrics/summary?type=cpu_usage&period=all" | jq .
print_success "Summary retrieved (all time)"

echo ""
print_info "GET $BASE_URL/api/metrics/summary?type=cpu_usage&period=daily"
curl -s "$BASE_URL/api/metrics/summary?type=cpu_usage&period=daily" | jq .
print_success "Summary retrieved (daily)"

echo ""
print_info "GET $BASE_URL/api/metrics/summary?type=memory_usage&period=all"
curl -s "$BASE_URL/api/metrics/summary?type=memory_usage&period=all" | jq .
print_success "Summary retrieved (memory)"

# 4. Test Caching (second request should be faster)
print_section "4. Testing Cache Performance"

print_info "First request (computes and caches)..."
time curl -s "$BASE_URL/api/metrics/summary?type=cpu_usage&period=all" > /dev/null

echo ""
print_info "Second request (served from cache)..."
time curl -s "$BASE_URL/api/metrics/summary?type=cpu_usage&period=all" > /dev/null

print_success "Cache test completed (second request should be faster)"

# 5. List Metrics
print_section "5. Listing Metrics"

print_info "GET $BASE_URL/api/metrics/list?limit=5"
curl -s "$BASE_URL/api/metrics/list?limit=5" | jq .
print_success "Listed last 5 metrics"

echo ""
print_info "GET $BASE_URL/api/metrics/list?type=cpu_usage&limit=3"
curl -s "$BASE_URL/api/metrics/list?type=cpu_usage&limit=3" | jq .
print_success "Listed last 3 cpu_usage metrics"

# 6. Circuit Breaker Status
print_section "6. Circuit Breaker Status"

print_info "GET $BASE_URL/api/circuit-breaker/status"
curl -s "$BASE_URL/api/circuit-breaker/status" | jq .
print_success "Circuit breaker status retrieved"

# 7. Test Rate Limiting
print_section "7. Testing Rate Limiting"

print_info "Making 12 requests to test rate limiting (limit: 10/min)..."

for i in {1..12}; do
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/metrics" \
        -H "Content-Type: application/json" \
        -d "{
            \"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",
            \"value\": 75,
            \"type\": \"test_rate_limit\"
        }")
    
    status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" == "201" ]; then
        echo "  Request $i: ✓ Accepted (201)"
    elif [ "$status_code" == "429" ]; then
        echo "  Request $i: ⚠ Rate limited (429)"
        print_success "Rate limiting is working!"
        break
    else
        echo "  Request $i: ? Unexpected status ($status_code)"
    fi
    
    sleep 0.5
done

# 8. Test Different Metric Types
print_section "8. Summary by Metric Type"

for metric_type in "cpu_usage" "memory_usage" "disk_usage"; do
    print_info "Summary for $metric_type:"
    curl -s "$BASE_URL/api/metrics/summary?type=$metric_type&period=all" | jq '{type, count, average_value, min_value, max_value}'
    echo ""
done

# 9. API Documentation
print_section "9. API Documentation"

print_info "Interactive API documentation available at:"
echo "  • Swagger UI: http://localhost:8000/docs"
echo "  • ReDoc:      http://localhost:8000/redoc"

echo ""
print_section "Demo Completed!"
echo ""
echo "You can now explore the API further using:"
echo "  • Swagger UI: http://localhost:8000/docs"
echo "  • curl commands from this script"
echo "  • Your favorite API client (Postman, Insomnia, etc.)"
echo ""
