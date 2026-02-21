# Quick Start Script for Resilient Analytics API (PowerShell)
# This script starts the application using docker-compose

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Resilient Analytics API - Quick Start" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Docker is not installed." -ForegroundColor Red
    Write-Host "Please install Docker from https://docs.docker.com/get-docker/" -ForegroundColor Yellow
    exit 1
}

# Check if docker-compose is installed
try {
    docker-compose --version | Out-Null
    Write-Host "✅ docker-compose is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: docker-compose is not installed." -ForegroundColor Red
    Write-Host "Please install docker-compose from https://docs.docker.com/compose/install/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Stop any existing containers
Write-Host "📦 Stopping existing containers..." -ForegroundColor Yellow
docker-compose down -v 2>$null
Write-Host ""

# Build the application
Write-Host "🔨 Building Docker images..." -ForegroundColor Yellow
docker-compose build
Write-Host ""

# Start the services
Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose up -d
Write-Host ""

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    $status = docker-compose ps
    if ($status -match "healthy") {
        Write-Host "✅ Services are healthy!" -ForegroundColor Green
        $healthy = $true
        break
    }
    
    $attempt++
    Write-Host "   Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    Write-Host "❌ Services failed to become healthy" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ Application started successfully!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 API Documentation:" -ForegroundColor Yellow
Write-Host "   Swagger UI: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   ReDoc:      http://localhost:8000/redoc" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Health Check:" -ForegroundColor Yellow
Write-Host "   curl http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "📝 View Logs:" -ForegroundColor Yellow
Write-Host "   docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "🛑 Stop Application:" -ForegroundColor Yellow
Write-Host "   docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Run Tests:" -ForegroundColor Yellow
Write-Host "   docker-compose run --rm app pytest" -ForegroundColor White
Write-Host ""

# Test the health endpoint
Write-Host "Testing health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Health check passed!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 Your API is ready to use!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Health check failed. Application may still be starting..." -ForegroundColor Yellow
    Write-Host "Please wait a moment and try: curl http://localhost:8000/health" -ForegroundColor Yellow
}

Write-Host ""
