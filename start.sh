#!/bin/bash
# Quick Start Script for Resilient Analytics API
# This script starts the application using docker-compose

set -e

echo "============================================"
echo "Resilient Analytics API - Quick Start"
echo "============================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed."
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed."
    echo "Please install docker-compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and docker-compose are installed"
echo ""

# Stop any existing containers
echo "📦 Stopping existing containers..."
docker-compose down -v 2>/dev/null || true
echo ""

# Build the application
echo "🔨 Building Docker images..."
docker-compose build
echo ""

# Start the services
echo "🚀 Starting services..."
docker-compose up -d
echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✅ Services are healthy!"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Services failed to become healthy"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ Application started successfully!"
echo "============================================"
echo ""
echo "📊 API Documentation:"
echo "   Swagger UI: http://localhost:8000/docs"
echo "   ReDoc:      http://localhost:8000/redoc"
echo ""
echo "🔍 Health Check:"
echo "   curl http://localhost:8000/health"
echo ""
echo "📝 View Logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop Application:"
echo "   docker-compose down"
echo ""
echo "🧪 Run Tests:"
echo "   docker-compose run --rm app pytest"
echo ""

# Test the health endpoint
echo "Testing health endpoint..."
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Health check passed!"
    echo ""
    echo "🎉 Your API is ready to use!"
else
    echo "⚠️  Health check failed. Application may still be starting..."
    echo "Please wait a moment and try: curl http://localhost:8000/health"
fi

echo ""
