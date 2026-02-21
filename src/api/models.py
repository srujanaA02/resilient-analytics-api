from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List


class MetricRequest(BaseModel):
    """Request model for creating a metric."""

    timestamp: datetime = Field(..., description="ISO 8601 timestamp")
    value: float = Field(..., description="Numeric metric value")
    type: str = Field(..., min_length=1, max_length=100, description="Metric type identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-02-19T12:00:00Z",
                "value": 75.5,
                "type": "cpu_usage",
            }
        }


class MetricResponse(BaseModel):
    """Response model for a single metric."""

    id: Optional[str] = None
    timestamp: datetime
    value: float
    type: str


class MetricSummary(BaseModel):
    """Summary of aggregated metrics."""

    type: str = Field(description="Metric type")
    period: str = Field(description="Time period (daily, hourly, all)")
    count: int = Field(description="Number of metrics in period")
    average_value: float = Field(description="Average value")
    min_value: float = Field(description="Minimum value")
    max_value: float = Field(description="Maximum value")
    latest_value: float = Field(description="Latest value")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "cpu_usage",
                "period": "daily",
                "count": 100,
                "average_value": 75.3,
                "min_value": 10.5,
                "max_value": 95.8,
                "latest_value": 80.2,
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "timestamp": "2026-02-19T12:00:00Z",
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    redis_connected: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status response."""

    state: str
    failure_count: int
    success_count: int
