"""
Telemetry middleware for automatic request/response tracking.

This middleware provides comprehensive tracking of HTTP requests including:
- Request/response time monitoring
- Request/response event tracking
- Distributed tracing integration
- Performance metrics collection
- Error tracking and alerting
- User activity monitoring

Integration Points:
- Automatic span creation for each request
- Performance threshold monitoring
- Business event tracking for API usage
- Security event tracking for authentication/authorization
- Rate limiting and usage metrics
"""

import time
import json
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from app.services.telemetry import (
    event_tracker, performance_monitor, distributed_tracer,
    metrics_collector, alert_manager,
    EventContext, EventCategory, EventLevel, SpanType,
    inject_trace_context, extract_trace_context,
    track_api_call, track_response_time, increment_metric
)


logger = logging.getLogger(__name__)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive telemetry middleware for FastAPI applications.
    
    Automatically tracks:
    - Request/response metrics
    - Performance data
    - Error tracking
    - Distributed tracing
    - User activity
    - Security events
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        """Initialize the telemetry middleware.
        
        Args:
            app: ASGI application
            exclude_paths: Paths to exclude from telemetry tracking
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health", "/docs", "/redoc", "/openapi.json",
            "/favicon.ico", "/metrics"
        ]
        
        # Track request statistics
        self.request_counts = {
            "total": 0,
            "by_method": {},
            "by_status": {},
            "errors": 0
        }
        
        logger.info("Telemetry middleware initialized")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and track telemetry data."""
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", request_id)
        
        # Extract or create trace context
        headers = dict(request.headers)
        trace_context = extract_trace_context(headers)
        
        # Create event context
        event_context = EventContext(
            request_id=request_id,
            correlation_id=correlation_id,
            source="http_request",
            environment="development"  # TODO: Get from config
        )
        
        # Set contexts for this request
        event_tracker.set_request_context(event_context)
        distributed_tracer.set_trace_context(trace_context)
        
        # Start distributed tracing span
        span_context = distributed_tracer.start_span(
            name=f"HTTP {request.method} {request.url.path}",
            span_type=SpanType.HTTP_REQUEST,
            service_name="fernando",
            operation_name=f"{request.method} {request.url.path}",
            parent_context=trace_context
        )
        
        # Add request attributes to span
        self._add_request_attributes(request, request_id, correlation_id)
        
        # Track request start
        start_time = time.time()
        self._track_request_start(request)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Track successful response
            await self._track_success_response(
                request, response, response_time, request_id
            )
            
            return response
            
        except Exception as e:
            # Track error response
            response_time = (time.time() - start_time) * 1000
            await self._track_error_response(
                request, e, response_time, request_id
            )
            raise
            
        finally:
            # End the tracing span
            if span_context:
                distributed_tracer.end_span()
            
            # Clear contexts
            event_tracker.set_request_context(None)
            distributed_tracer.set_trace_context(None)
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from tracking."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    def _add_request_attributes(self, request: Request, request_id: str, correlation_id: str):
        """Add request attributes to the current span."""
        distributed_tracer.add_span_attribute("http.request_id", request_id)
        distributed_tracer.add_span_attribute("http.correlation_id", correlation_id)
        distributed_tracer.add_span_attribute("http.method", request.method)
        distributed_tracer.add_span_attribute("http.url", str(request.url))
        distributed_tracer.add_span_attribute("http.user_agent", request.headers.get("user-agent", ""))
        distributed_tracer.add_span_attribute("http.content_length", request.headers.get("content-length", "0"))
        
        # Add client information
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        distributed_tracer.add_span_attribute("http.client_ip", client_host)
        distributed_tracer.add_span_attribute("http.client_port", client_port)
    
    def _track_request_start(self, request: Request):
        """Track request start event."""
        event_tracker.track_api_event(
            method=request.method,
            endpoint=request.url.path,
            status_code=0,  # Not yet available
            response_time_ms=0,
            data={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        # Increment request counter
        increment_metric("http.requests.total", 1.0, {
            "method": request.method,
            "endpoint": request.url.path
        })
        
        # Update request statistics
        self.request_counts["total"] += 1
        method_key = request.method
        self.request_counts["by_method"][method_key] = self.request_counts["by_method"].get(method_key, 0) + 1
    
    async def _track_success_response(self, request: Request, response: Response,
                                    response_time: float, request_id: str):
        """Track successful response."""
        # Track API event
        event_tracker.track_api_event(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            response_time_ms=response_time,
            data={
                "request_id": request_id,
                "response_size": len(response.body) if hasattr(response, 'body') else 0
            }
        )
        
        # Track performance metrics
        performance_monitor.track_request_performance(
            method=request.method,
            endpoint=request.url.path,
            response_time_ms=response_time,
            status_code=response.status_code,
            context={
                "request_id": request_id,
                "user_agent": request.headers.get("user-agent", "")
            }
        )
        
        # Track response metrics
        increment_metric("http.responses.total", 1.0, {
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "success": "true" if response.status_code < 400 else "false"
        })
        
        # Track response time histogram
        metrics_collector.record_histogram(
            "http.response_time_ms",
            response_time,
            labels={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": response.status_code
            },
            tags=["http", "response_time"]
        )
        
        # Update statistics
        status_key = f"{response.status_code // 100}xx"
        self.request_counts["by_status"][status_key] = self.request_counts["by_status"].get(status_key, 0) + 1
        
        # Add span attributes
        distributed_tracer.add_span_attribute("http.status_code", response.status_code)
        distributed_tracer.add_span_attribute("http.response_time_ms", response_time)
        distributed_tracer.add_span_attribute("http.response_size", len(response.body) if hasattr(response, 'body') else 0)
        
        # Track specific business events
        await self._track_business_events(request, response, response_time)
    
    async def _track_error_response(self, request: Request, error: Exception,
                                  response_time: float, request_id: str):
        """Track error response."""
        # Track error event
        event_tracker.track_error(error, context=event_tracker.get_current_context())
        
        # Track API event with error status
        event_tracker.track_api_event(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,  # Generic error status
            response_time_ms=response_time,
            data={
                "request_id": request_id,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )
        
        # Track error metrics
        increment_metric("http.errors.total", 1.0, {
            "method": request.method,
            "endpoint": request.url.path,
            "error_type": type(error).__name__
        })
        
        self.request_counts["errors"] += 1
        
        # Add error attributes to span
        distributed_tracer.add_span_attribute("http.status_code", 500)
        distributed_tracer.add_span_attribute("http.response_time_ms", response_time)
        distributed_tracer.add_span_attribute("error", "true")
        distributed_tracer.add_span_attribute("error.type", type(error).__name__)
        distributed_tracer.add_span_attribute("error.message", str(error))
        
        # Check for critical error patterns that might need alerting
        if response_time > 5000:  # 5 seconds
            alert_manager.check_custom_condition(
                lambda: True,  # Always trigger
                f"Slow Response: {request.method} {request.url.path}",
                f"Response time {response_time:.2f}ms exceeds 5s threshold",
                AlertSeverity.HIGH
            )
    
    async def _track_business_events(self, request: Request, response: Response, response_time: float):
        """Track business-specific events based on endpoint patterns."""
        path = request.url.path
        
        # Authentication endpoints
        if "/auth/" in path:
            if response.status_code == 200:
                event_tracker.track_event(
                    name="auth.success",
                    category=EventCategory.SECURITY,
                    level=EventLevel.INFO,
                    data={
                        "method": request.method,
                        "endpoint": path,
                        "user_agent": request.headers.get("user-agent", "")
                    }
                )
            elif response.status_code == 401:
                event_tracker.track_event(
                    name="auth.failure",
                    category=EventCategory.SECURITY,
                    level=EventLevel.WARNING,
                    data={
                        "method": request.method,
                        "endpoint": path,
                        "client_ip": request.client.host if request.client else "unknown"
                    }
                )
        
        # Billing endpoints
        elif "/billing/" in path:
            event_tracker.track_billing_event(
                event_name="api_request",
                data={
                    "method": request.method,
                    "endpoint": path,
                    "status_code": response.status_code,
                    "response_time_ms": response_time
                }
            )
        
        # Payment endpoints
        elif "/payments/" in path:
            if response.status_code == 200:
                event_tracker.track_event(
                    name="payment.api_success",
                    category=EventCategory.PAYMENT,
                    level=EventLevel.INFO,
                    data={
                        "method": request.method,
                        "endpoint": path,
                        "response_time_ms": response_time
                    }
                )
            else:
                event_tracker.track_event(
                    name="payment.api_error",
                    category=EventCategory.PAYMENT,
                    level=EventLevel.ERROR,
                    data={
                        "method": request.method,
                        "endpoint": path,
                        "status_code": response.status_code,
                        "response_time_ms": response_time
                    }
                )
        
        # Document processing endpoints
        elif "/documents/" in path or "/extractions/" in path:
            event_tracker.track_event(
                name="document.api_request",
                category=EventCategory.DOCUMENT,
                level=EventLevel.INFO,
                data={
                    "method": request.method,
                    "endpoint": path,
                    "status_code": response.status_code,
                    "response_time_ms": response_time
                }
            )
        
        # License management endpoints
        elif "/licenses/" in path:
            event_tracker.track_event(
                name="license.api_request",
                category=EventCategory.LICENSE,
                level=EventLevel.INFO,
                data={
                    "method": request.method,
                    "endpoint": path,
                    "status_code": response.status_code,
                    "response_time_ms": response_time
                }
            )
    
    def get_request_statistics(self) -> Dict[str, Any]:
        """Get request statistics."""
        return {
            "total_requests": self.request_counts["total"],
            "requests_by_method": self.request_counts["by_method"],
            "requests_by_status": self.request_counts["by_status"],
            "error_count": self.request_counts["errors"],
            "error_rate": (self.request_counts["errors"] / max(self.request_counts["total"], 1)) * 100
        }


# Helper function to create telemetry middleware
def create_telemetry_middleware(app: ASGIApp, exclude_paths: Optional[list] = None) -> TelemetryMiddleware:
    """Create and configure telemetry middleware."""
    return TelemetryMiddleware(app, exclude_paths)


# Decorator for function-level telemetry
def track_function_execution(service_name: str = "unknown"):
    """Decorator to track function execution with telemetry."""
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Start span
            span_context = distributed_tracer.start_span(
                name=f"function.{func.__name__}",
                span_type=SpanType.INTERNAL,
                service_name=service_name
            )
            
            start_time = time.time()
            
            try:
                # Track function start
                event_tracker.track_event(
                    name=f"function_start.{func.__name__}",
                    category=EventCategory.SYSTEM,
                    level=EventLevel.INFO,
                    data={"args_count": len(args), "kwargs_count": len(kwargs)}
                )
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Track success
                duration = (time.time() - start_time) * 1000
                event_tracker.track_event(
                    name=f"function_success.{func.__name__}",
                    category=EventCategory.SYSTEM,
                    level=EventLevel.INFO,
                    data={
                        "duration_ms": duration,
                        "result_type": type(result).__name__
                    }
                )
                
                # Track performance
                performance_monitor.record_performance_metric(
                    f"function.{func.__name__}.duration_ms",
                    duration,
                    {"service": service_name},
                    ["function", service_name]
                )
                
                return result
                
            except Exception as e:
                # Track error
                duration = (time.time() - start_time) * 1000
                event_tracker.track_error(e)
                
                performance_monitor.record_performance_metric(
                    f"function.{func.__name__}.error_duration_ms",
                    duration,
                    {"service": service_name, "error": type(e).__name__},
                    ["function", "error", service_name]
                )
                
                raise
            
            finally:
                # End span
                if span_context:
                    distributed_tracer.end_span()
        
        return wrapper
    return decorator


# Integration helper for existing FastAPI applications
def setup_telemetry_for_app(app, exclude_paths: Optional[list] = None):
    """
    Setup comprehensive telemetry for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        exclude_paths: Paths to exclude from telemetry tracking
    """
    # Add telemetry middleware
    app.add_middleware(TelemetryMiddleware, exclude_paths=exclude_paths)
    
    # Add health check endpoint for telemetry services
    @app.get("/health/telemetry")
    async def telemetry_health():
        """Health check endpoint for telemetry services."""
        from app.services.telemetry import get_telemetry_health_status
        
        health_status = get_telemetry_health_status()
        
        # Check if all services are healthy
        all_healthy = all(
            service.get("status") == "healthy" 
            for service in health_status.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": health_status,
            "timestamp": time.time()
        }
    
    # Add metrics endpoint for Prometheus scraping
    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        from app.services.telemetry import metrics_collector
        
        return metrics_collector.export_metrics(format_type="prometheus")
    
    # Add events endpoint for debugging
    @app.get("/debug/events")
    async def debug_events(limit: int = 100):
        """Debug endpoint for recent events."""
        events = event_tracker.get_events(limit=limit)
        return {
            "events": [
                {
                    "id": event.id,
                    "name": event.name,
                    "category": event.category.value,
                    "level": event.level.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                }
                for event in events
            ],
            "total": len(events)
        }
    
    # Add traces endpoint for debugging
    @app.get("/debug/traces")
    async def debug_traces(limit: int = 10):
        """Debug endpoint for recent traces."""
        tracer_stats = distributed_tracer.get_trace_statistics()
        slow_traces = distributed_tracer.get_slowest_traces(limit)
        
        return {
            "statistics": tracer_stats,
            "slowest_traces": slow_traces
        }
    
    # Add alerts endpoint for debugging
    @app.get("/debug/alerts")
    async def debug_alerts():
        """Debug endpoint for active alerts."""
        active_alerts = alert_manager.get_active_alerts()
        alert_stats = alert_manager.get_alert_statistics()
        
        return {
            "active_alerts": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "category": alert.rule_category.value,
                    "status": alert.status.value,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "current_value": alert.current_value,
                    "threshold": alert.threshold
                }
                for alert in active_alerts
            ],
            "statistics": alert_stats
        }
    
    logger.info("Telemetry setup completed for FastAPI application")


# Background task for telemetry service initialization
async def initialize_telemetry_services():
    """Initialize telemetry services in background."""
    from app.core.config import settings
    
    if not settings.TELEMETRY_ENABLED:
        logger.info("Telemetry services disabled in configuration")
        return
    
    from app.services.telemetry import (
        metrics_collector, event_tracker, performance_monitor,
        distributed_tracer, alert_manager, initialize_telemetry_services as init_services
    )
    
    # Configure based on settings
    if settings.METRICS_ENABLED:
        metrics_collector.max_metrics = settings.METRICS_MAX_DATA_POINTS
        logger.info(f"Metrics collection configured: {settings.METRICS_MAX_DATA_POINTS} max data points")
    
    if settings.DISTRIBUTED_TRACING_ENABLED:
        distributed_tracer.max_traces = settings.TRACING_MAX_TRACES
        distributed_tracer.set_sampling_rate(settings.TRACING_SAMPLING_RATE)
        logger.info(f"Distributed tracing configured: {settings.TRACING_SAMPLING_RATE} sampling rate")
    
    if settings.ALERTS_ENABLED:
        alert_manager.max_alerts = settings.ALERTS_MAX_ALERTS
        logger.info(f"Alert manager configured: {settings.ALERTS_MAX_ALERTS} max alerts")
    
    # Initialize all services
    await init_services()
    
    logger.info("Telemetry services initialization completed")