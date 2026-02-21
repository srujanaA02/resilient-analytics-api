# Demo Script for Resilient Analytics API (PowerShell)
# This script demonstrates all API endpoints with example requests

$BaseUrl = "http://localhost:8000"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Resilient Analytics API - Demo Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Function to print section headers
function Print-Section {
    param($title)
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host $title -ForegroundColor Blue
    Write-Host "============================================" -ForegroundColor Blue
    Write-Host ""
}

# Function to print success messages
function Print-Success {
    param($message)
    Write-Host "✓ $message" -ForegroundColor Green
}

# Function to print info messages
function Print-Info {
    param($message)
    Write-Host "→ $message" -ForegroundColor Yellow
}

# 1. Health Check
Print-Section "1. Health Check"
Print-Info "GET $BaseUrl/health"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
    $response | ConvertTo-Json -Depth 10
    Print-Success "Health check completed"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Create Metrics
Print-Section "2. Creating Sample Metrics"

$metricTypes = @("cpu_usage", "memory_usage", "disk_usage")
$baseValues = @(60, 70, 80)

for ($i = 1; $i -le 5; $i++) {
    for ($j = 0; $j -lt 3; $j++) {
        $metricType = $metricTypes[$j]
        $baseValue = $baseValues[$j]
        $value = $baseValue + (Get-Random -Maximum 20)
        
        $timestamp = (Get-Date).AddHours(-$i).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        
        Print-Info "Creating $metricType metric (value: $value)"
        
        $body = @{
            timestamp = $timestamp
            value = $value
            type = $metricType
        } | ConvertTo-Json
        
        try {
            $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics" -Method Post -Body $body -ContentType "application/json"
            Write-Host "  ✓ Created" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Print-Success "Sample metrics created"

# 3. Get Metrics Summary
Print-Section "3. Getting Metrics Summary"

Print-Info "GET $BaseUrl/api/metrics/summary?type=cpu_usage&period=all"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=cpu_usage&period=all"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Summary retrieved (all time)"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Print-Info "GET $BaseUrl/api/metrics/summary?type=cpu_usage&period=daily"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=cpu_usage&period=daily"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Summary retrieved (daily)"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Print-Info "GET $BaseUrl/api/metrics/summary?type=memory_usage&period=all"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=memory_usage&period=all"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Summary retrieved (memory)"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Test Caching
Print-Section "4. Testing Cache Performance"

Print-Info "First request (computes and caches)..."
$stopwatch1 = [System.Diagnostics.Stopwatch]::StartNew()
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=cpu_usage&period=all" | Out-Null
    $stopwatch1.Stop()
    Write-Host "Time: $($stopwatch1.ElapsedMilliseconds) ms"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Print-Info "Second request (served from cache)..."
$stopwatch2 = [System.Diagnostics.Stopwatch]::StartNew()
try {
    Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=cpu_usage&period=all" | Out-Null
    $stopwatch2.Stop()
    Write-Host "Time: $($stopwatch2.ElapsedMilliseconds) ms"
    Print-Success "Cache test completed (second request should be faster)"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. List Metrics
Print-Section "5. Listing Metrics"

Print-Info "GET $BaseUrl/api/metrics/list?limit=5"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/list?limit=5"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Listed last 5 metrics"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Print-Info "GET $BaseUrl/api/metrics/list?type=cpu_usage&limit=3"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/list?type=cpu_usage&limit=3"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Listed last 3 cpu_usage metrics"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Circuit Breaker Status
Print-Section "6. Circuit Breaker Status"

Print-Info "GET $BaseUrl/api/circuit-breaker/status"
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/circuit-breaker/status"
    $response | ConvertTo-Json -Depth 10
    Print-Success "Circuit breaker status retrieved"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. Test Rate Limiting
Print-Section "7. Testing Rate Limiting"

Print-Info "Making 12 requests to test rate limiting (limit: 10/min)..."

for ($i = 1; $i -le 12; $i++) {
    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $body = @{
        timestamp = $timestamp
        value = 75
        type = "test_rate_limit"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics" -Method Post -Body $body -ContentType "application/json"
        Write-Host "  Request $i : ✓ Accepted (201)" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 429) {
            Write-Host "  Request $i : ⚠ Rate limited (429)" -ForegroundColor Yellow
            Print-Success "Rate limiting is working!"
            break
        } else {
            Write-Host "  Request $i : ? Unexpected error" -ForegroundColor Red
        }
    }
    
    Start-Sleep -Milliseconds 500
}

# 8. Test Different Metric Types
Print-Section "8. Summary by Metric Type"

foreach ($metricType in @("cpu_usage", "memory_usage", "disk_usage")) {
    Print-Info "Summary for $metricType :"
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/metrics/summary?type=$metricType&period=all"
        $summary = @{
            type = $response.type
            count = $response.count
            average_value = $response.average_value
            min_value = $response.min_value
            max_value = $response.max_value
        }
        $summary | ConvertTo-Json
        Write-Host ""
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 9. API Documentation
Print-Section "9. API Documentation"

Print-Info "Interactive API documentation available at:"
Write-Host "  • Swagger UI: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • ReDoc:      http://localhost:8000/redoc" -ForegroundColor White

Write-Host ""
Print-Section "Demo Completed!"
Write-Host ""
Write-Host "You can now explore the API further using:" -ForegroundColor Cyan
Write-Host "  • Swagger UI: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • PowerShell commands from this script" -ForegroundColor White
Write-Host "  • Your favorite API client (Postman, Insomnia, etc.)" -ForegroundColor White
Write-Host ""
