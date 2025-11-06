"""
Telemetry Service Setup and Usage Guide

This file demonstrates how to set up and use the comprehensive telemetry
services for the Fernando platform.

## Quick Setup

### 1. Update Requirements

Add to requirements.txt:
```
psutil>=5.9.0
aiohttp>=3.8.0
```

### 2. Initialize in FastAPI Application

```python
from fastapi import FastAPI
from app.middleware.telemetry_middleware import setup_telemetry_for_app
from app.services.telemetry import initialize_telemetry_services

app = FastAPI()

# Setup comprehensive telemetry
@app.on_event("startup")
async def startup_event():
    await initialize_telemetry_services()
    setup_telemetry_for_app(app)

@app.on_event("shutdown")  
async def shutdown_event():
    from app.services.telemetry import shutdown_telemetry_services
    await shutdown_telemetry_services()
```

### 3. Use in Business Logic

```python
from app.services.telemetry import (
    metrics_collector, event_tracker, performance_monitor
)
from app.middleware.telemetry_decorators import billing_telemetry

@billing_telemetry()
async def process_payment(payment_data: dict):
    # This will automatically track:
    # - Performance metrics
    # - Billing events
    # - Success/failure rates
    # - Error tracking
    pass

# Manual telemetry tracking
def my_business_function():
    # Record a business metric
    metrics_collector.record_metric("daily_active_users", 150, MetricType.GAUGE)
    
    # Track an event
    event_tracker.track_business_event("feature_used", {"feature": "export"})
    
    # Monitor performance
    with performance_monitor.record_timer("complex_calculation"):
        result = calculate_something_complex()
    
    return result
```

## Detailed Usage Examples

### Metrics Collection

```python
from app.services.telemetry import (
    metrics_collector, MetricType, record_business_metric
)

# System metrics (automatic)
metrics_collector.record_metric("app.users.total", 1000, MetricType.GAUGE)

# Business metrics
record_business_metric("revenue.daily", 2500.50, {"currency": "USD"})

# Custom metrics
metrics_collector.record_histogram("api.response_times", 250.5)

# Counters
metrics_collector.increment_counter("payments.processed", 1.0)
```

### Event Tracking

```python
from app.services.telemetry import (
    event_tracker, EventCategory, EventLevel
)

# User events
event_tracker.track_user_action("document_uploaded", "user123")

# Business events
event_tracker.track_business_event("license_activated", {
    "license_type": "enterprise",
    "duration_months": 12
})

# System events
event_tracker.track_system_event("service_restart", EventLevel.INFO)

# Error tracking
try:
    risky_operation()
except Exception as e:
    event_tracker.track_error(e)
```

### Performance Monitoring

```python
from app.services.telemetry import performance_monitor, performance_timer

# Context manager
with performance_timer("database_query"):
    results = db.query("SELECT * FROM users")

# Manual tracking
performance_monitor.track_database_query(
    query="SELECT * FROM orders WHERE status = 'pending'",
    duration_ms=150.5
)

# API performance
performance_monitor.track_request_performance(
    method="POST",
    endpoint="/api/payments",
    response_time_ms=500.0,
    status_code=200
)
```

### Distributed Tracing

```python
from app.services.telemetry import (
    distributed_tracer, SpanType, traced_operation, trace_function
)

# Function decorator
@trace_function(SpanType.INTERNAL, "payment_service")
def process_payment():
    # Function execution is automatically traced
    return payment_result

# Context manager
with traced_operation("complex_calculation", SpanType.INTERNAL):
    result = perform_complex_calculation()
    distributed_tracer.add_attribute("calculation_type", "financial")

# Manual span management
context = distributed_tracer.start_span("custom_operation")
try:
    # Your operation
    pass
finally:
    distributed_tracer.end_span()
```

### Alert Management

```python
from app.services.telemetry import (
    alert_manager, create_alert_rule, AlertSeverity, AlertCategory
)

# Create custom alert rule
rule = create_alert_rule(
    name="High Payment Failure Rate",
    metric_name="payment.failure_rate",
    condition=">",
    threshold=5.0,
    severity=AlertSeverity.HIGH,
    category=AlertCategory.BUSINESS
)
alert_manager.add_alert_rule(rule)

# Custom condition alerts
alert_manager.check_custom_condition(
    condition_func=lambda: is_payment_gateway_down(),
    title="Payment Gateway Down",
    message="Payment processing is currently unavailable",
    severity=AlertSeverity.CRITICAL
)
```

### Business Logic Decorators

```python
from app.middleware.telemetry_decorators import (
    billing_telemetry, user_activity_telemetry,
    document_telemetry, business_operation_telemetry
)

@billing_telemetry()
async def process_subscription(user_id: str, plan: str):
    # Automatically tracks billing events, metrics, and performance
    pass

@user_activity_telemetry()
async def generate_report(user_id: str, report_type: str):
    # Tracks user actions and engagement
    pass

@document_telemetry()
async def process_document(file_path: str):
    # Tracks document processing performance and events
    pass

# Context manager for complex operations
with business_operation_telemetry("order_fulfillment", EventCategory.BUSINESS) as ctx:
    ctx.add_attribute("order_type", "premium")
    ctx.add_metric("fulfillment_steps", 5)
    
    # Your business logic
    process_order()
    
    ctx.add_event("fulfillment_completed", {"processing_time": "fast"})
```

### Background Tasks

```python
from app.services.telemetry import (
    start_telemetry_background_tasks,
    configure_telemetry_task
)

# Start background tasks
await start_telemetry_background_tasks()

# Configure specific tasks
configure_telemetry_task("metrics_aggregation", interval=300, enabled=True)
configure_telemetry_task("external_sync", interval=3600, enabled=False)

# Check task status
from app.services.telemetry import get_telemetry_tasks_status
status = get_telemetry_tasks_status()
```

## Configuration

Add to your `.env` file:

```bash
# Telemetry Settings
TELEMETRY_ENABLED=true
TELEMETRY_VERBOSE=false

# Metrics Collection
METRICS_ENABLED=true
METRICS_MAX_DATA_POINTS=10000
METRICS_RETENTION_HOURS=24

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED=true
PERFORMANCE_SLOW_QUERY_THRESHOLD=1000.0

# Distributed Tracing
DISTRIBUTED_TRACING_ENABLED=true
TRACING_SAMPLING_RATE=1.0

# Alert Management
ALERTS_ENABLED=true
ALERTS_EMAIL_NOTIFICATIONS=true
```

## Integration Points

### 1. Automatic Request Tracking
The middleware automatically tracks:
- Request/response times
- HTTP status codes
- Error rates
- User agent information
- Client IP addresses

### 2. Business Event Correlation
Events are automatically correlated with:
- User IDs
- Session IDs
- Request IDs
- Correlation IDs

### 3. External System Integration
Ready for integration with:
- Prometheus (metrics export)
- Jaeger (tracing)
- DataDog (monitoring)
- New Relic (APM)

## Monitoring Endpoints

After setup, these endpoints will be available:
- `/health/telemetry` - Telemetry services health check
- `/metrics` - Prometheus metrics
- `/debug/events` - Recent events (debug only)
- `/debug/traces` - Recent traces (debug only)
- `/debug/alerts` - Active alerts (debug only)

## Best Practices

### 1. Use Appropriate Decorators
- `@billing_telemetry()` for payment/billing logic
- `@document_telemetry()` for document processing
- `@user_activity_telemetry()` for user-facing features

### 2. Choose Correct Metric Types
- Use `MetricType.COUNTER` for counting occurrences
- Use `MetricType.GAUGE` for current values
- Use `MetricType.HISTOGRAM` for distributions

### 3. Context is Important
Always include relevant context in events:
- User IDs
- Request IDs
- Resource IDs
- Timestamps

### 4. Performance Impact
- Use sampling for high-volume operations
- Monitor memory usage of telemetry services
- Clean up old data regularly

### 5. Alert Thresholds
- Set realistic thresholds based on historical data
- Use multiple severity levels
- Avoid alert fatigue

## Troubleshooting

### High Memory Usage
If telemetry services use too much memory:
```python
# Reduce data retention
metrics_collector.max_metrics = 5000  # Reduce from 10000
event_tracker.max_events = 25000     # Reduce from 50000
```

### Performance Impact
If telemetry impacts performance:
```python
# Reduce sampling rate
distributed_tracer.set_sampling_rate(0.1)  # Sample 10% instead of 100%

# Disable verbose logging
event_tracker.verbose_logging = False
```

### Missing Events
If events are not appearing:
1. Check service initialization
2. Verify middleware is added to FastAPI app
3. Check configuration settings
4. Review logs for errors

## Example Integration with Existing Code

```python
# Before telemetry
async def process_payment(payment_data: dict):
    result = await payment_gateway.charge(payment_data)
    return result

# After telemetry
@billing_telemetry("payment_processing")
async def process_payment(payment_data: dict):
    with performance_timer("payment_gateway_call"):
        result = await payment_gateway.charge(payment_data)
    
    if result.success:
        event_tracker.track_billing_event("payment_success", 
            amount=payment_data["amount"],
            currency=payment_data["currency"]
        )
    else:
        event_tracker.track_billing_event("payment_failure",
            amount=payment_data["amount"],
            error=result.error
        )
    
    return result
```

This telemetry infrastructure provides comprehensive observability
for the Fernando platform with minimal performance impact and easy integration.
"""